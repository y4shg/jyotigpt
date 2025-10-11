package app.y4shg.jyotigpt

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import io.flutter.plugin.common.MethodChannel.MethodCallHandler
import io.flutter.plugin.common.MethodChannel.Result
import kotlinx.coroutines.*
import org.json.JSONArray
import org.json.JSONObject

class BackgroundStreamingService : Service() {
    private var wakeLock: PowerManager.WakeLock? = null
    private val activeStreams = mutableSetOf<String>()
    private var isForeground = false
    private var currentForegroundType: Int = 0

    companion object {
        const val CHANNEL_ID = "jyotigpt_streaming_channel"
        const val NOTIFICATION_ID = 1001
        const val ACTION_START = "START_STREAMING"
        const val ACTION_STOP = "STOP_STREAMING"
        const val EXTRA_REQUIRES_MICROPHONE = "requiresMicrophone"
    }

    override fun onCreate() {
        super.onCreate()
        println("BackgroundStreamingService: Service created")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = createMinimalNotification()
        val desiredType = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            resolveForegroundServiceType(intent)
        } else {
            0
        }

        if (!isForeground) {
            if (!startForegroundInternal(notification, desiredType)) {
                stopSelf()
                return START_NOT_STICKY
            }
        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q &&
            currentForegroundType != desiredType
        ) {
            updateForegroundType(notification, desiredType)
        }

        when (intent?.action) {
            ACTION_START -> {
                acquireWakeLock()
                println("BackgroundStreamingService: Started foreground service")
            }
            ACTION_STOP -> {
                stopStreaming()
            }
            "KEEP_ALIVE" -> {
                keepAlive()
            }
        }

        return START_STICKY // Restart if killed by system
    }

    private fun startForegroundInternal(notification: Notification, type: Int): Boolean {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                startForeground(NOTIFICATION_ID, notification, type)
                currentForegroundType = type
            } else {
                @Suppress("DEPRECATION")
                startForeground(NOTIFICATION_ID, notification)
            }
            isForeground = true
            true
        } catch (e: SecurityException) {
            println("BackgroundStreamingService: Failed to enter foreground: ${e.message}")
            false
        }
    }

    private fun updateForegroundType(notification: Notification, type: Int) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return
        try {
            startForeground(NOTIFICATION_ID, notification, type)
            currentForegroundType = type
        } catch (e: SecurityException) {
            println("BackgroundStreamingService: Unable to update foreground type: ${e.message}")
        }
    }

    private fun resolveForegroundServiceType(intent: Intent?): Int {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return 0

        val requiresMicrophone = intent?.getBooleanExtra(EXTRA_REQUIRES_MICROPHONE, false) ?: false
        if (requiresMicrophone) {
            if (hasRecordAudioPermission()) {
                return ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE or
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            }
            println("BackgroundStreamingService: Microphone permission missing; falling back to data sync type")
        }

        return ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
    }

    private fun hasRecordAudioPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            this,
            android.Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun createMinimalNotification(): Notification {
        // Create a minimal, silent notification (required for foreground service)
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("JyotiGPT")
            .setContentText("Background service active")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setPriority(NotificationCompat.PRIORITY_MIN)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setVisibility(NotificationCompat.VISIBILITY_SECRET)
            .setOngoing(true)
            .setShowWhen(false)
            .setSilent(true)
            .build()
    }
    
    private fun acquireWakeLock() {
        if (wakeLock?.isHeld == true) return

        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "JyotiGPT::StreamingWakeLock"
        ).apply {
            acquire(3 * 60 * 60 * 1000L) // 3 hours max (refreshed every 5 minutes)
        }
        println("BackgroundStreamingService: Wake lock acquired")
    }
    
    private fun releaseWakeLock() {
        wakeLock?.let {
            if (it.isHeld) {
                it.release()
                println("BackgroundStreamingService: Wake lock released")
            }
        }
        wakeLock = null
    }
    
    private fun keepAlive() {
        // Refresh wake lock to extend background processing time
        releaseWakeLock()
        acquireWakeLock()
        println("BackgroundStreamingService: Keep alive - wake lock refreshed")
    }
    
    private fun stopStreaming() {
        activeStreams.clear()
        releaseWakeLock()
        stopForeground(true)
        stopSelf()
        isForeground = false
        println("BackgroundStreamingService: Service stopped")
    }

    override fun onDestroy() {
        releaseWakeLock()
        isForeground = false
        super.onDestroy()
        println("BackgroundStreamingService: Service destroyed")
    }

    override fun onBind(intent: Intent?): IBinder? = null
}

class BackgroundStreamingHandler(private val activity: MainActivity) : MethodCallHandler {
    private lateinit var channel: MethodChannel
    private lateinit var context: Context
    private lateinit var sharedPrefs: SharedPreferences

    private val activeStreams = mutableSetOf<String>()
    private val streamsRequiringMic = mutableSetOf<String>()
    private var backgroundJob: Job? = null
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    
    companion object {
        private const val CHANNEL_NAME = "jyotigpt/background_streaming"
        private const val PREFS_NAME = "jyotigpt_stream_states"
        private const val STREAM_STATES_KEY = "active_streams"
    }

    fun setup(flutterEngine: FlutterEngine) {
        channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL_NAME)
        channel.setMethodCallHandler(this)
        context = activity.applicationContext
        sharedPrefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        
        createNotificationChannel()
    }

    override fun onMethodCall(call: MethodCall, result: Result) {
        when (call.method) {
            "startBackgroundExecution" -> {
                val streamIds = call.argument<List<String>>("streamIds")
                val requiresMic = call.argument<Boolean>("requiresMicrophone") ?: false
                if (streamIds != null) {
                    startBackgroundExecution(streamIds, requiresMic)
                    result.success(null)
                } else {
                    result.error("INVALID_ARGS", "Stream IDs required", null)
                }
            }
            
            "stopBackgroundExecution" -> {
                val streamIds = call.argument<List<String>>("streamIds")
                if (streamIds != null) {
                    stopBackgroundExecution(streamIds)
                    result.success(null)
                } else {
                    result.error("INVALID_ARGS", "Stream IDs required", null)
                }
            }
            
            "keepAlive" -> {
                keepAlive()
                result.success(null)
            }
            
            "saveStreamStates" -> {
                val states = call.argument<List<Map<String, Any>>>("states")
                val reason = call.argument<String>("reason")
                if (states != null) {
                    saveStreamStates(states, reason ?: "unknown")
                    result.success(null)
                } else {
                    result.error("INVALID_ARGS", "States required", null)
                }
            }
            
            "recoverStreamStates" -> {
                result.success(recoverStreamStates())
            }
            
            else -> {
                result.notImplemented()
            }
        }
    }

    private fun startBackgroundExecution(streamIds: List<String>, requiresMic: Boolean) {
        activeStreams.addAll(streamIds)
        streamsRequiringMic.retainAll(activeStreams)
        if (requiresMic) {
            streamsRequiringMic.addAll(streamIds)
        }

        if (activeStreams.isNotEmpty()) {
            startForegroundService()
            startBackgroundMonitoring()
        }
    }

    private fun stopBackgroundExecution(streamIds: List<String>) {
        activeStreams.removeAll(streamIds.toSet())
        streamsRequiringMic.removeAll(streamIds.toSet())

        if (activeStreams.isEmpty()) {
            stopForegroundService()
            stopBackgroundMonitoring()
        }
    }

    private fun startForegroundService() {
        try {
            val serviceIntent = Intent(context, BackgroundStreamingService::class.java)
            serviceIntent.putExtra("streamCount", activeStreams.size)
            serviceIntent.putExtra(
                BackgroundStreamingService.EXTRA_REQUIRES_MICROPHONE,
                streamsRequiringMic.isNotEmpty(),
            )
            serviceIntent.action = BackgroundStreamingService.ACTION_START

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(serviceIntent)
            } else {
                context.startService(serviceIntent)
            }
        } catch (e: Exception) {
            println("BackgroundStreamingHandler: Failed to start foreground service: ${e.message}")
            // Clear active streams as we couldn't start the service
            activeStreams.clear()
            streamsRequiringMic.clear()
        }
    }

    private fun stopForegroundService() {
        val serviceIntent = Intent(context, BackgroundStreamingService::class.java)
        serviceIntent.action = BackgroundStreamingService.ACTION_STOP
        context.startService(serviceIntent)
    }

    private fun startBackgroundMonitoring() {
        backgroundJob?.cancel()
        backgroundJob = scope.launch {
            while (activeStreams.isNotEmpty()) {
                delay(30000) // Check every 30 seconds
                
                // Notify Dart side to check stream health
                channel.invokeMethod("checkStreams", null, object : MethodChannel.Result {
                    override fun success(result: Any?) {
                        when (result) {
                            is Int -> {
                                if (result == 0) {
                                    activeStreams.clear()
                                    stopForegroundService()
                                }
                            }
                        }
                    }
                    
                    override fun error(errorCode: String, errorMessage: String?, errorDetails: Any?) {
                        println("BackgroundStreamingHandler: Error checking streams: $errorMessage")
                    }
                    
                    override fun notImplemented() {
                        println("BackgroundStreamingHandler: checkStreams method not implemented")
                    }
                })
            }
        }
    }

    private fun stopBackgroundMonitoring() {
        backgroundJob?.cancel()
        backgroundJob = null
    }

    private fun keepAlive() {
        // Just notify the service to refresh
        val serviceIntent = Intent(context, BackgroundStreamingService::class.java)
        serviceIntent.action = "KEEP_ALIVE"
        serviceIntent.putExtra("streamCount", activeStreams.size)
        serviceIntent.putExtra(
            BackgroundStreamingService.EXTRA_REQUIRES_MICROPHONE,
            streamsRequiringMic.isNotEmpty(),
        )
        context.startService(serviceIntent)
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = "Background Service"
            val descriptionText = "Background service for JyotiGPT"
            val importance = NotificationManager.IMPORTANCE_MIN
            val channel = NotificationChannel(BackgroundStreamingService.CHANNEL_ID, name, importance).apply {
                description = descriptionText
                setShowBadge(false)
                enableLights(false)
                enableVibration(false)
                setSound(null, null)
                lockscreenVisibility = Notification.VISIBILITY_SECRET
            }

            val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun saveStreamStates(states: List<Map<String, Any>>, reason: String) {
        try {
            val jsonArray = JSONArray()
            for (state in states) {
                val jsonObject = JSONObject()
                for ((key, value) in state) {
                    jsonObject.put(key, value)
                }
                jsonArray.put(jsonObject)
            }
            
            sharedPrefs.edit()
                .putString(STREAM_STATES_KEY, jsonArray.toString())
                .putLong("saved_timestamp", System.currentTimeMillis())
                .putString("saved_reason", reason)
                .apply()
                
            println("BackgroundStreamingHandler: Saved ${states.size} stream states (reason: $reason)")
        } catch (e: Exception) {
            println("BackgroundStreamingHandler: Failed to save stream states: ${e.message}")
        }
    }

    private fun recoverStreamStates(): List<Map<String, Any>> {
        return try {
            val savedStates = sharedPrefs.getString(STREAM_STATES_KEY, null) ?: return emptyList()
            val timestamp = sharedPrefs.getLong("saved_timestamp", 0)
            val reason = sharedPrefs.getString("saved_reason", "unknown")
            
            // Check if states are not too old (max 1 hour)
            val age = System.currentTimeMillis() - timestamp
            if (age > 3600000) { // 1 hour in milliseconds
                println("BackgroundStreamingHandler: Stream states too old (${age / 1000}s), discarding")
                sharedPrefs.edit().remove(STREAM_STATES_KEY).apply()
                return emptyList()
            }
            
            val jsonArray = JSONArray(savedStates)
            val result = mutableListOf<Map<String, Any>>()
            
            for (i in 0 until jsonArray.length()) {
                val jsonObject = jsonArray.getJSONObject(i)
                val map = mutableMapOf<String, Any>()
                
                val keys = jsonObject.keys()
                while (keys.hasNext()) {
                    val key = keys.next()
                    val value = jsonObject.get(key)
                    map[key] = value
                }
                
                result.add(map)
            }
            
            println("BackgroundStreamingHandler: Recovered ${result.size} stream states (reason: $reason, age: ${age / 1000}s)")
            
            // Clear saved states after recovery
            sharedPrefs.edit().remove(STREAM_STATES_KEY).apply()
            
            result
        } catch (e: Exception) {
            println("BackgroundStreamingHandler: Failed to recover stream states: ${e.message}")
            emptyList()
        }
    }

    fun cleanup() {
        scope.cancel()
        stopBackgroundMonitoring()
        stopForegroundService()
    }
}
