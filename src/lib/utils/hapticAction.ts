import { triggerHaptic } from './haptics';

export function haptic(node: HTMLElement, pattern: string | number | number[] = 'success') {
    const handleClick = () => {
        triggerHaptic(pattern);
    };

    node.addEventListener('click', handleClick);

    return {
        update(newPattern: string | number | number[]) {
            pattern = newPattern;
        },
        destroy() {
            node.removeEventListener('click', handleClick);
        }
    };
}
