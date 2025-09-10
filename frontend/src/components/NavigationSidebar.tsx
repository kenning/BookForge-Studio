import React from 'react';
import { useLocation, useNavigate } from 'react-router';

interface NavigationItem {
  path: string;
  label: string;
  icon: string;
}

interface NavigationSidebarProps {
  isDirty?: boolean;
}

const NavigationSidebar: React.FC<NavigationSidebarProps> = ({ isDirty = false }) => {
  const location = useLocation();
  const navigate = useNavigate();

  const navigationItems: NavigationItem[] = [
    {
      path: '/text-workflows',
      label: 'Text Workflows',
      icon: '📝',
    },
    {
      path: '/actors',
      label: 'Actors',
      icon: '🎭',
    },
    {
      path: '/voice-modes',
      label: 'Voice Modes',
      icon: '🎨',
    },
    {
      path: '/timeline',
      label: 'Timeline',
      icon: '📽️',
    },
  ];

  const handleNavigation = (path: string) => {
    if (isDirty) {
      const confirmed = window.confirm('Leave without saving changes?');
      if (!confirmed) {
        return;
      }
    }
    navigate(path);
  };

  return (
    <div className="navigation-sidebar navigation-sidebar-compact">
      <div className="navigation-header">
        <div className="navigation-header-text">BookForge Studio</div>
      </div>

      <nav className="navigation-menu">
        {navigationItems.map(item => (
          <div className="navigation-item-container">
            <button
              key={item.path}
              className={`navigation-item ${location.pathname === item.path ? 'active' : ''}`}
              onClick={() => handleNavigation(item.path)}
              title={item.label}
            >
              <span className="navigation-label">{item.label}</span>
              <span className="navigation-icon">{item.icon}</span>
            </button>
          </div>
        ))}
      </nav>
    </div>
  );
};

export default NavigationSidebar;
