import { useState } from 'react';

/**
 * Awake/Asleep Mode Toggle
 * 
 * @param {object} props
 * @param {boolean} props.isAwake - Current mode state
 * @param {function} props.onToggle - Toggle callback
 * @param {boolean} props.disabled - Whether toggle is disabled
 */
export function ModeToggle({ isAwake, onToggle, disabled = false }) {
  const [isTransitioning, setIsTransitioning] = useState(false);

  const handleToggle = () => {
    if (disabled || isTransitioning) return;

    setIsTransitioning(true);
    // Small delay to allow visual transition feedback
    setTimeout(() => {
      onToggle();
      setTimeout(() => setIsTransitioning(false), 50);
    }, 150);
  };

  return (
    <button
      onClick={handleToggle}
      disabled={disabled || isTransitioning}
      className={`
        relative w-14 h-14 rounded-full flex items-center justify-center
        transition-all duration-300 ease-out
        shadow-lg hover:shadow-xl hover:scale-110 active:scale-95
        disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100
        ${isAwake 
          ? 'bg-gradient-to-br from-amber-400 to-orange-500 shadow-amber-500/30' 
          : 'bg-gradient-to-br from-indigo-500 to-purple-600 shadow-indigo-500/30'
        }
      `}
      title={isAwake ? 'Click to sleep' : 'Click to wake'}
      aria-label={isAwake ? 'Switch to asleep mode' : 'Switch to awake mode'}
    >
      <span 
        className={`
          text-2xl transition-transform duration-300
          ${isTransitioning ? 'scale-75 rotate-90' : 'scale-100 rotate-0'}
        `}
        aria-hidden="true"
      >
        {isAwake ? '☀️' : '🌙'}
      </span>
      
      {/* Glow effect */}
      <div 
        className={`
          absolute inset-0 rounded-full blur-xl -z-10 opacity-50
          transition-colors duration-300
          ${isAwake ? 'bg-amber-400' : 'bg-indigo-500'}
        `}
        aria-hidden="true"
      />
    </button>
  );
}

export default ModeToggle;
