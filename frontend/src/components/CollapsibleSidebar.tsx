import React, { useState } from 'react';

interface CollapsibleSidebarProps {
  children: React.ReactNode;
  defaultCollapsed?: boolean;
  className?: string;
}

const CollapsibleSidebar: React.FC<CollapsibleSidebarProps> = ({
  children,
  defaultCollapsed = false,
  className = '',
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);

  const toggleCollapsed = () => {
    setIsCollapsed(!isCollapsed);
  };

  return (
    <div className={`collapsible-sidebar ${isCollapsed ? 'collapsed' : 'expanded'} ${className}`}>
      <div className="sidebar-content">{children}</div>
      <button
        className="collapse-handle"
        onClick={toggleCollapsed}
        title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {isCollapsed ? '→' : '←'}
      </button>
    </div>
  );
};

export default CollapsibleSidebar;
