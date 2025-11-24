import React from 'react';

function Spinner({ size = 'page' }) {
  if (size === 'inline') {
    return <div className="spinner" style={{ width: '20px', height: '20px', borderWidth: '3px' }}></div>;
  }
  
  return (
    <div className="full-page-spinner">
      <div className="spinner"></div>
    </div>
  );
}

export default Spinner;