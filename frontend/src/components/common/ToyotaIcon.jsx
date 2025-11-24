import React from 'react';
import { SvgIcon } from '@mui/material';

/**
 * Toyota-inspired icon - Three overlapping ellipses representing Toyota's logo style
 */
function ToyotaIcon(props) {
  return (
    <SvgIcon {...props} viewBox="0 0 24 24">
      {/* Outer ellipse (horizontal) */}
      <ellipse
        cx="12"
        cy="12"
        rx="10"
        ry="6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      
      {/* Inner left ellipse (vertical) */}
      <ellipse
        cx="9"
        cy="12"
        rx="3"
        ry="5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      
      {/* Inner right ellipse (vertical) */}
      <ellipse
        cx="15"
        cy="12"
        rx="3"
        ry="5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      />
    </SvgIcon>
  );
}

export default ToyotaIcon;






