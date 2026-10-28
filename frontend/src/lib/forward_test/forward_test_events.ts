// The events of one forward test for the Logs tab of the forward test page: the start, each interruption and its
// end, the stop, and the end time of a forward test that is not stopped. Oldest first.
import { describeInterruptionReason, type ForwardTest } from './forward_test_api';

export interface ForwardTestEvent {
  timeUtc: string;
  text: string;
}

export function listForwardTestEvents(forwardTest: ForwardTest): ForwardTestEvent[] {
  const events: ForwardTestEvent[] = [{ timeUtc: forwardTest.created_at_utc, text: 'Started' }];
  for (const interruption of forwardTest.interruptions) {
    events.push({
      timeUtc: interruption.started_at_utc,
      text: `Interrupted: ${describeInterruptionReason(interruption.reason)}`,
    });
    if (interruption.ended_at_utc !== null) {
      events.push({ timeUtc: interruption.ended_at_utc, text: 'Continued' });
    }
  }
  if (forwardTest.stopped_at_utc !== null) {
    events.push({ timeUtc: forwardTest.stopped_at_utc, text: 'Stopped' });
  } else if (forwardTest.end_time_utc !== null) {
    events.push({ timeUtc: forwardTest.end_time_utc, text: 'Planned stop' });
  }
  return events.toSorted((first, second) => Date.parse(first.timeUtc) - Date.parse(second.timeUtc));
}
