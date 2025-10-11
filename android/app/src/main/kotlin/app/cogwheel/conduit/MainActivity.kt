package app.y4shg.jyotigpt

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import android.os.Build
import android.os.Bundle
import androidx.core.view.WindowCompat

class MainActivity : FlutterActivity() {
    private lateinit var backgroundStreamingHandler: BackgroundStreamingHandler
    
    override fun onCreate(savedInstanceState: Bundle?) {
        // Ensure content draws behind system bars (backwards compatible helper)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        
        super.onCreate(savedInstanceState)
    }
    
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        
        // Initialize background streaming handler
        backgroundStreamingHandler = BackgroundStreamingHandler(this)
        backgroundStreamingHandler.setup(flutterEngine)
    }
    
    override fun onDestroy() {
        super.onDestroy()
        if (::backgroundStreamingHandler.isInitialized) {
            backgroundStreamingHandler.cleanup()
        }
    }
}
