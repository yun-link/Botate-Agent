import React from 'react';
import { Shield, X } from 'lucide-react';
import type { PermissionRequest } from '../types';

interface PermissionConfirmProps {
  permissionRequest: PermissionRequest;
  onConfirm: () => void;
  onDeny: () => void;
}

export const PermissionConfirm: React.FC<PermissionConfirmProps> = ({
  permissionRequest,
  onConfirm,
  onDeny,
}) => {
  return (
    <div className="permission-confirm-block">
      <div className="permission-confirm-header">
        <div className="permission-confirm-title">
          <Shield size={16} className="permission-icon" />
          <span>权限确认</span>
        </div>
      </div>
      
      <div className="permission-confirm-content">
        <div className="permission-info">
          <div className="permission-tool-name">
            工具: <span>{permissionRequest.tool_name}</span>
          </div>
          <div className="permission-reason">
            原因: <span>{permissionRequest.reason}</span>
          </div>
        </div>
        
        <div className="permission-buttons">
          <button 
            className="permission-btn permission-btn-allow"
            onClick={onConfirm}
          >
            授权
          </button>
          <button 
            className="permission-btn permission-btn-deny"
            onClick={onDeny}
          >
            <X size={14} />
            拒绝
          </button>
        </div>
      </div>
    </div>
  );
};
