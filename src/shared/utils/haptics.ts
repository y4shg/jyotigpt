import { WebHaptics } from 'web-haptics';

let instance: WebHaptics | null = null;

function getInstance(): WebHaptics {
    if (!instance) {
        instance = new WebHaptics();
    }
    return instance;
}

/**
 * Fire haptic feedback. Silently no-ops on unsupported platforms (desktop).
 *
 * @param type - Preset name: "light" | "medium" | "heavy" | "success" | "warning" | "error" | "selection"
 */
export const hapticTrigger = (type?: string): void => {
    try {
        getInstance().trigger(type as any);
    } catch {
        // Silently ignore – device may not support vibration
    }
};
