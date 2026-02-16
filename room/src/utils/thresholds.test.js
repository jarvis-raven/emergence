/**
 * Tests for threshold utilities
 *
 * Run with: npm test thresholds.test.js
 */

import { describe, it, expect } from 'vitest';
import {
  DEFAULT_THRESHOLD_RATIOS,
  computeGraduatedThresholds,
  getThresholdBand,
  getBandColors,
  getBandIcon,
  getBandLabel,
  enrichDriveWithThresholds,
  groupDrivesByBand,
} from './thresholds.js';

describe('Threshold Utilities', () => {
  describe('computeGraduatedThresholds', () => {
    it('should compute thresholds from base threshold', () => {
      const thresholds = computeGraduatedThresholds(20);

      expect(thresholds.available).toBe(6); // 20 * 0.30
      expect(thresholds.elevated).toBe(15); // 20 * 0.75
      expect(thresholds.triggered).toBe(20); // 20 * 1.0
      expect(thresholds.crisis).toBe(30); // 20 * 1.5
      expect(thresholds.emergency).toBe(40); // 20 * 2.0
    });

    it('should use custom ratios when provided', () => {
      const customRatios = {
        available: 0.5,
        elevated: 0.8,
        triggered: 1.0,
        crisis: 1.2,
        emergency: 1.5,
      };

      const thresholds = computeGraduatedThresholds(10, customRatios);

      expect(thresholds.available).toBe(5);
      expect(thresholds.elevated).toBe(8);
      expect(thresholds.triggered).toBe(10);
      expect(thresholds.crisis).toBe(12);
      expect(thresholds.emergency).toBe(15);
    });
  });

  describe('getThresholdBand', () => {
    const thresholds = {
      available: 6,
      elevated: 15,
      triggered: 20,
      crisis: 30,
      emergency: 40,
    };

    it('should return neutral for pressure below available', () => {
      expect(getThresholdBand(5, thresholds)).toBe('neutral');
      expect(getThresholdBand(0, thresholds)).toBe('neutral');
    });

    it('should return available for pressure at or above available threshold', () => {
      expect(getThresholdBand(6, thresholds)).toBe('available');
      expect(getThresholdBand(10, thresholds)).toBe('available');
    });

    it('should return elevated for pressure at or above elevated threshold', () => {
      expect(getThresholdBand(15, thresholds)).toBe('elevated');
      expect(getThresholdBand(18, thresholds)).toBe('elevated');
    });

    it('should return triggered for pressure at or above triggered threshold', () => {
      expect(getThresholdBand(20, thresholds)).toBe('triggered');
      expect(getThresholdBand(25, thresholds)).toBe('triggered');
    });

    it('should return crisis for pressure at or above crisis threshold', () => {
      expect(getThresholdBand(30, thresholds)).toBe('crisis');
      expect(getThresholdBand(35, thresholds)).toBe('crisis');
    });

    it('should return emergency for pressure at or above emergency threshold', () => {
      expect(getThresholdBand(40, thresholds)).toBe('emergency');
      expect(getThresholdBand(100, thresholds)).toBe('emergency');
    });
  });

  describe('getBandColors', () => {
    it('should return color scheme for each band', () => {
      expect(getBandColors('neutral')).toHaveProperty('bg');
      expect(getBandColors('available')).toHaveProperty('gradient');
      expect(getBandColors('triggered')).toHaveProperty('text');
    });

    it('should return neutral colors for unknown band', () => {
      const colors = getBandColors('unknown');
      expect(colors).toEqual(getBandColors('neutral'));
    });
  });

  describe('getBandIcon', () => {
    it('should return correct icon for each band', () => {
      expect(getBandIcon('available')).toBe('✓');
      expect(getBandIcon('elevated')).toBe('⚡');
      expect(getBandIcon('triggered')).toBe('🔥');
      expect(getBandIcon('crisis')).toBe('⚠️');
      expect(getBandIcon('emergency')).toBe('🚨');
    });
  });

  describe('getBandLabel', () => {
    it('should return human-readable label for each band', () => {
      expect(getBandLabel('available')).toBe('Available');
      expect(getBandLabel('elevated')).toBe('Elevated');
      expect(getBandLabel('triggered')).toBe('Triggered');
      expect(getBandLabel('crisis')).toBe('Crisis');
      expect(getBandLabel('emergency')).toBe('Emergency');
    });
  });

  describe('enrichDriveWithThresholds', () => {
    it('should enrich drive with threshold data', () => {
      const drive = {
        name: 'CARE',
        pressure: 18,
        threshold: 20,
        percentage: 90,
      };

      const enriched = enrichDriveWithThresholds(drive);

      expect(enriched).toHaveProperty('thresholds');
      expect(enriched).toHaveProperty('band');
      expect(enriched).toHaveProperty('bandColors');
      expect(enriched).toHaveProperty('bandIcon');
      expect(enriched).toHaveProperty('bandLabel');

      // 18 is >= 15 (elevated) but < 20 (triggered)
      expect(enriched.band).toBe('elevated');
      expect(enriched.thresholds.triggered).toBe(20);
    });

    it('should correctly identify emergency band', () => {
      const drive = {
        name: 'CARE',
        pressure: 45,
        threshold: 20,
        percentage: 225,
      };

      const enriched = enrichDriveWithThresholds(drive);

      // 45 is >= 40 (emergency)
      expect(enriched.band).toBe('emergency');
      expect(enriched.bandIcon).toBe('🚨');
    });
  });

  describe('groupDrivesByBand', () => {
    it('should group drives into bands', () => {
      const drives = [
        { name: 'CARE', pressure: 5, threshold: 20, percentage: 25 },
        { name: 'READING', pressure: 18, threshold: 20, percentage: 90 },
        { name: 'CREATIVE', pressure: 22, threshold: 20, percentage: 110 },
        { name: 'SOCIAL', pressure: 35, threshold: 20, percentage: 175 },
      ];

      const grouped = groupDrivesByBand(drives);

      expect(grouped.neutral).toHaveLength(1);
      expect(grouped.neutral[0].name).toBe('CARE');

      expect(grouped.elevated).toHaveLength(1);
      expect(grouped.elevated[0].name).toBe('READING');

      expect(grouped.triggered).toHaveLength(1);
      expect(grouped.triggered[0].name).toBe('CREATIVE');

      expect(grouped.crisis).toHaveLength(1);
      expect(grouped.crisis[0].name).toBe('SOCIAL');

      expect(grouped.emergency).toHaveLength(0);
      expect(grouped.available).toHaveLength(0);
    });

    it('should return empty arrays for unpopulated bands', () => {
      const drives = [{ name: 'CARE', pressure: 10, threshold: 20, percentage: 50 }];

      const grouped = groupDrivesByBand(drives);

      expect(grouped.available).toHaveLength(1);
      expect(grouped.neutral).toHaveLength(0);
      expect(grouped.elevated).toHaveLength(0);
      expect(grouped.triggered).toHaveLength(0);
      expect(grouped.crisis).toHaveLength(0);
      expect(grouped.emergency).toHaveLength(0);
    });
  });
});
