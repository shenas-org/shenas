import { describe, it, expect } from 'vitest';
import {
  formatTime,
  formatDate,
  dayKey,
  computeBarPosition,
} from '../timeline-utils';

describe('timeline-utils', () => {
  describe('formatTime', () => {
    it('formats a date as HH:MM', () => {
      const date = new Date('2026-04-12T14:30:00');
      expect(formatTime(date)).toBe('14:30');
    });

    it('handles midnight', () => {
      const date = new Date('2026-04-12T00:00:00');
      expect(formatTime(date)).toBe('00:00');
    });
  });

  describe('formatDate', () => {
    it('formats a date as MMM DD, YYYY', () => {
      const date = new Date('2026-04-12T14:30:00');
      expect(formatDate(date)).toMatch(/Apr \d{2}, 2026/);
    });
  });

  describe('dayKey', () => {
    it('returns a string key for the date (YYYY-MM-DD)', () => {
      const date = new Date('2026-04-12T14:30:00');
      const key = dayKey(date);
      expect(key).toBe('2026-04-12');
    });

    it('handles different dates', () => {
      const date1 = new Date('2026-01-01T00:00:00');
      const date2 = new Date('2026-12-31T23:59:59');
      expect(dayKey(date1)).toBe('2026-01-01');
      expect(dayKey(date2)).toBe('2026-12-31');
    });
  });

  describe('computeBarPosition', () => {
    it('computes left and width for a full-day event', () => {
      const start = new Date('2026-04-12T00:00:00');
      const end = new Date('2026-04-12T23:59:59');
      const day = new Date('2026-04-12T00:00:00');
      const position = computeBarPosition(start, end, day);
      expect(position.left).toBe(0);
      expect(position.width).toBeCloseTo(100, 1);
    });

    it('computes left and width for a morning event', () => {
      const start = new Date('2026-04-12T08:00:00');
      const end = new Date('2026-04-12T09:00:00');
      const day = new Date('2026-04-12T00:00:00');
      const position = computeBarPosition(start, end, day);
      expect(position.left).toBeCloseTo((8 / 24) * 100, 1);
      expect(position.width).toBeCloseTo((1 / 24) * 100, 1);
    });

    it('computes position for an afternoon event', () => {
      const start = new Date('2026-04-12T14:00:00');
      const end = new Date('2026-04-12T15:30:00');
      const day = new Date('2026-04-12T00:00:00');
      const position = computeBarPosition(start, end, day);
      expect(position.left).toBeCloseTo((14 / 24) * 100, 1);
      expect(position.width).toBeCloseTo((1.5 / 24) * 100, 1);
    });
  });
});
