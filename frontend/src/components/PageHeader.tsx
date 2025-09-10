import React, { useState, useEffect } from 'react';
import { useTheme } from '../App';
import { modelsApi } from '../api/api';
import { ServiceStatus } from '../types/readableBackendTypes';

interface PageHeaderProps {
  title: string;
  children?: React.ReactNode;
}

interface MicroserviceStatusProps {
  services: ServiceStatus[];
  backendDown: boolean;
}

const MicroserviceStatus: React.FC<MicroserviceStatusProps> = ({ services, backendDown }) => {
  if (backendDown) {
    return (
      <div className="microservice-status">
        <div className="service-indicator backend-down">Backend is down</div>
      </div>
    );
  }

  const onlineServices = services
    .filter(service => service.is_running)
    .map(service => {
      // @ts-ignore
      const healthData: any = service.health_data?.data?.[0];
      const isLoaded = healthData?.model_loaded || service.service_name === 'local_llm';
      const statusClass = isLoaded ? 'loaded' : 'unloaded';
      const displayName = (healthData?.model_name as string) || service.service_name || '';

      return (
        <div key={service.service_name} className={`service-indicator ${statusClass}`}>
          <>
            {displayName}
            {!isLoaded && ' (Unloaded)'}
          </>
        </div>
      );
    });
  const displayThis = onlineServices.length > 0 ? onlineServices : 'None';

  return <div className="microservice-status">Online: {displayThis}</div>;
};

const PageHeader: React.FC<PageHeaderProps> = ({ title, children }) => {
  const { theme, toggleTheme } = useTheme();
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [backendDown, setBackendDown] = useState(false);

  const checkServicesStatus = async () => {
    try {
      const response = await modelsApi.getServicesStatus();
      setServices(response.services);
      setBackendDown(false);
    } catch (error) {
      console.error('Failed to fetch services status:', error);
      setBackendDown(true);
      setServices([]);
    }
  };

  useEffect(() => {
    // Check status immediately
    checkServicesStatus();

    // Set up polling every 5 seconds
    const interval = setInterval(checkServicesStatus, 5000);

    return () => clearInterval(interval);
  }, []);

  return (
    <header className="page-header">
      <h1>{title}</h1>
      <div className="page-header-actions">
        <MicroserviceStatus services={services} backendDown={backendDown} />
        {children}
        <button
          className="theme-toggle-btn"
          onClick={toggleTheme}
          title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
        >
          {theme === 'light' ? '🌙' : '☀️'}
        </button>
      </div>
    </header>
  );
};

export default PageHeader;
