import { ReactNode } from 'react';
import LogPanel from './LogPanel';
export const NotSidebarContentWithWrapper = ({
  children,
  className,
  style,
  wrapperStyle,
}: {
  children: ReactNode;
  wrapperStyle?: React.CSSProperties;
  style?: React.CSSProperties;
  className?: string;
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', ...wrapperStyle }}>
      <div className={`not-sidebar-content ${className || ''}`} style={style}>
        {children}
      </div>
      <LogPanel />
    </div>
  );
};
