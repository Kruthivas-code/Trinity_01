import { useState, Children } from 'react';

export const Tabs = ({ children, defaultTab = 0, className = '' }) => {
  const [activeTab, setActiveTab] = useState(defaultTab);
  const tabs = Children.toArray(children).filter(
    child => child?.type === Tab || child?.type?.displayName === 'Tab'
  );

  return (
    <div className={`tabs-container my-6 ${className}`} data-testid="tabs">
      <div className="flex border-b border-slate-800 overflow-x-auto">
        {tabs.map((tab, index) => (
          <button key={index} onClick={() => setActiveTab(index)}
            className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-colors border-b-2 -mb-px ${
              activeTab === index
                ? 'text-[#188455] border-[#188455]'
                : 'text-slate-400 border-transparent hover:text-white hover:border-slate-600'
            }`}
            data-testid={`tab-${index}`}>
            {tab.props.label || `Tab ${index + 1}`}
          </button>
        ))}
      </div>
      <div className="pt-4">
        {tabs.map((tab, index) => (
          <div key={index} className={activeTab === index ? 'block' : 'hidden'} data-testid={`tab-content-${index}`}>
            {tab.props.children}
          </div>
        ))}
      </div>
    </div>
  );
};

export const Tab = ({ label, children, className = '' }) => {
  return <div className={className}>{children}</div>;
};

Tab.displayName = 'Tab';
