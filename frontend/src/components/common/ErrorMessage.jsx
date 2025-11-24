import React from 'react';

function ErrorMessage({ message, onRetry }) {
  return (
    <div className="error-message">
      <p>Oops! Something went wrong.</p>
      <p><em>{message || 'Could not load the requested data.'}</em></p>
      {onRetry && <button onClick={onRetry}>Try Again</button>}
    </div>
  );
}

export default ErrorMessage;