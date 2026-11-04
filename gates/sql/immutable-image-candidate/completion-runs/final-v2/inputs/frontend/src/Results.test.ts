import { expect, test } from 'vitest';
import { resultLabel } from './Results';
/** Keep run and check SAT/UNSAT interpretations distinct and bounded. @returns Nothing. */
function reportsCommandSemantics(): void {
  expect(resultLabel('SAT','run')).toBe('Instance found');
  expect(resultLabel('SAT','check')).toBe('Counterexample found');
  expect(resultLabel('UNSAT','run')).toBe('No instance within bounds');
  expect(resultLabel('UNSAT','check')).toBe('No counterexample within bounds');
}
/** Keep inconclusive statuses separate from absence evidence. @returns Nothing. */
function reportsInconclusive(): void {
  expect(resultLabel('TIMEOUT','check')).toBe('Time limit reached');
  expect(resultLabel('UNKNOWN','run')).toBe('Inconclusive');
}
test('interprets run and check results',reportsCommandSemantics);
test('does not treat inconclusive statuses as absence',reportsInconclusive);
