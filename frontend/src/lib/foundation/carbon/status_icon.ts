// The Carbon status icon of each status kind. The icon shape differs for each kind, so a status does not depend on
// the color only.

import CheckmarkFilled16 from '@carbon/icons/es/checkmark--filled/16.js';
import CircleDash16 from '@carbon/icons/es/circle-dash/16.js';
import ErrorFilled16 from '@carbon/icons/es/error--filled/16.js';
import InProgress16 from '@carbon/icons/es/in-progress/16.js';
import WarningAltFilled16 from '@carbon/icons/es/warning--alt--filled/16.js';
import type { CarbonIconNode } from './carbon_icon';

export type StatusKind = 'success' | 'in-progress' | 'warning' | 'error' | 'neutral';

export function findStatusIcon(statusKind: StatusKind): CarbonIconNode {
  switch (statusKind) {
    case 'success':
      return CheckmarkFilled16;
    case 'in-progress':
      return InProgress16;
    case 'warning':
      return WarningAltFilled16;
    case 'error':
      return ErrorFilled16;
    case 'neutral':
      return CircleDash16;
  }
}
