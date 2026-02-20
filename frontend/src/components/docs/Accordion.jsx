import { useState, Children } from 'react';
import { ChevronDown } from 'lucide-react';

export const Accordion = ({ children, className = '' }) => {
  const items = Children.toArray(children).filter(
    child => child?.type === AccordionItem || child?.type?.displayName === 'AccordionItem'
  );

  if (items.length === 0 && children) {
    return (
      <div className={`my-6 border border-gray-200 dark:border-slate-800 rounded-lg divide-y divide-gray-200 dark:divide-slate-800 ${className}`} data-testid="accordion">
        {children}
      </div>
    );
  }

  return (
    <div className={`my-6 border border-gray-200 dark:border-slate-800 rounded-lg divide-y divide-gray-200 dark:divide-slate-800 ${className}`} data-testid="accordion">
      {items}
    </div>
  );
};

export const AccordionItem = ({ title, children, defaultOpen = false, className = '' }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className={`${className}`} data-testid="accordion-item">
      <button onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3.5 flex items-center justify-between text-left hover:bg-gray-50 dark:hover:bg-slate-900/50 transition-colors"
        data-testid="accordion-trigger">
        <span className="!text-gray-900 dark:!text-white font-medium">{title}</span>
        <ChevronDown className={`w-4 h-4 text-gray-400 dark:text-[#999999] transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      <div className={`overflow-hidden transition-all duration-200 ${isOpen ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}>
        <div className="px-4 pb-4 [&_p]:!text-gray-600 dark:[&_p]:!text-[#999999] [&_code]:!text-[#00A1B2] dark:[&_code]:!text-[#00A1B2] [&_strong]:!text-gray-900 dark:[&_strong]:!text-white [&_a]:!text-[#00A1B2]"
          data-testid="accordion-content">
          {children}
        </div>
      </div>
    </div>
  );
};

AccordionItem.displayName = 'AccordionItem';
