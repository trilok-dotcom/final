import React, { useState } from 'react';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

interface PageContainerProps {
  children: React.ReactNode;
}

export const PageContainer: React.FC<PageContainerProps> = ({ children }) => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="h-screen w-screen flex flex-col bg-[#090d16] text-slate-100 overflow-hidden">
      <TopBar onToggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)} />
      
      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar 
          collapsed={sidebarCollapsed} 
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)} 
        />

        <main className="flex-1 flex flex-col overflow-y-auto bg-[#090d16] relative min-h-0">
          {children}
        </main>
      </div>
    </div>
  );
};
