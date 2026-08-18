import React from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

export function LoadingSpinner({ size = 'md', label = 'Loading...' }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-6 h-6 border-2',
    lg: 'w-8 h-8 border-3',
  };

  return (
    <div className="flex items-center justify-center space-x-2" role="status">
      <div
        className={`${sizeClasses[size]} animate-spin rounded-full border-blue-500 border-t-transparent`}
      />
      {label && <span className="text-sm text-gray-400 font-medium">{label}</span>}
    </div>
  );
}
