import React from 'react';

/**
 * TridentIcon - Trinity's brand icon
 * A minimalist, sleek trident inspired by Maserati's logo
 * Represents power, precision, and the Trinity brand
 */
export const TridentIcon = ({ 
  size = 24, 
  className = '',
  strokeWidth = 2,
  ...props 
}) => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`trident-icon ${className}`}
      {...props}
    >
      {/* Center prong - tallest */}
      <path d="M12 2v16" />
      <path d="M12 2l-1.5 3" />
      <path d="M12 2l1.5 3" />
      
      {/* Left prong - curved elegantly */}
      <path d="M12 7c-2 -1.5 -3.5 -3 -4 -5" />
      <path d="M8 2l-0.5 2" />
      <path d="M8 2l1.2 1.2" />
      
      {/* Right prong - curved elegantly */}
      <path d="M12 7c2 -1.5 3.5 -3 4 -5" />
      <path d="M16 2l0.5 2" />
      <path d="M16 2l-1.2 1.2" />
      
      {/* Handle */}
      <path d="M12 18v4" strokeWidth={strokeWidth * 1.2} />
      
      {/* Cross guard */}
      <path d="M9 18h6" />
    </svg>
  );
};

/**
 * TridentLogo - Full brand logo with text
 */
export const TridentLogo = ({ 
  size = 'default',
  showText = true,
  className = '' 
}) => {
  const sizes = {
    sm: { icon: 20, text: 'text-base' },
    default: { icon: 24, text: 'text-lg' },
    lg: { icon: 32, text: 'text-xl' }
  };
  
  const { icon, text } = sizes[size] || sizes.default;
  
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <TridentIcon size={icon} className="text-primary" />
      {showText && (
        <span className={`brand ${text} font-bold tracking-tight`}>
          Trinity
        </span>
      )}
    </div>
  );
};

export default TridentIcon;
