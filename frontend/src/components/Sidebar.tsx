import React from 'react';
import { Plus, File, Settings, LogOut } from 'lucide-react';
import './Sidebar.css';

interface SidebarProps {
  selectedFile: string | null;
  onNewChat: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ selectedFile, onNewChat }) => {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <span className="logo-icon">🧠</span>
          <span className="logo-text">KnowAssist</span>
        </div>
      </div>

      <div className="sidebar-content">
        <button className="new-chat-btn" onClick={onNewChat}>
          <Plus size={20} />
          <span>New Chat</span>
        </button>

        {selectedFile && (
          <div className="current-file-section">
            <h3 className="section-title">Current Document</h3>
            <div className="file-item">
              <File size={18} />
              <span className="file-name" title={selectedFile}>
                {selectedFile.length > 20 ? selectedFile.substring(0, 17) + '...' : selectedFile}
              </span>
            </div>
          </div>
        )}

        <div className="sidebar-footer">
          <button className="sidebar-btn">
            <Settings size={18} />
            <span>Settings</span>
          </button>
          <button className="sidebar-btn">
            <LogOut size={18} />
            <span>Help</span>
          </button>
        </div>
      </div>

      <div className="sidebar-credits">
        <p>Knowledge Assistant v1.0</p>
        <p className="credits-subtitle">Powered by RAG</p>
      </div>
    </div>
  );
};

export default Sidebar;
