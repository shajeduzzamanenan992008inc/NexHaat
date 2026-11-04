import React, { useState, useEffect, useRef } from 'react';
import {
  Calendar as CalendarIcon,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Check,
  RotateCcw,
  Clock,
  Sparkles,
} from 'lucide-react';
import {
  DateRange,
  getDateRangePreset,
  formatDateDisplay,
  formatDateRangeDisplay,
  calculateDaysBetween,
} from '../lib/searchAnalytics';

export interface DateRangePickerProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
  className?: string;
  align?: 'left' | 'right';
}

interface PresetOption {
  id: string;
  label: string;
  description: string;
}

const PRESET_OPTIONS: PresetOption[] = [
  { id: 'today', label: 'Today', description: 'Single day performance' },
  { id: 'yesterday', label: 'Yesterday', description: 'Prior 24 hour queries' },
  { id: 'last7days', label: 'Last 7 Days', description: 'Past week trend' },
  { id: 'last14days', label: 'Last 14 Days', description: 'Bi-weekly trajectory' },
  { id: 'last30days', label: 'Last 30 Days', description: 'Monthly discovery analysis' },
  { id: 'thisMonth', label: 'This Month', description: 'Month-to-date queries' },
  { id: 'lastMonth', label: 'Last Month', description: 'Full previous calendar month' },
  { id: 'last90days', label: 'Last 90 Days', description: 'Quarterly macro demand' },
];

export const DateRangePicker: React.FC<DateRangePickerProps> = ({
  value,
  onChange,
  className = '',
  align = 'right',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Provisional draft state while popover is open
  const [draftStart, setDraftStart] = useState<string>(value.startDate);
  const [draftEnd, setDraftEnd] = useState<string>(value.endDate);
  const [activePreset, setActivePreset] = useState<string | undefined>(value.preset || 'last7days');
  const [hoveredDate, setHoveredDate] = useState<string | null>(null);

  // Month currently displayed in calendar view (default to month of draftEnd or Oct 2026)
  const [viewYear, setViewYear] = useState<number>(2026);
  const [viewMonth, setViewMonth] = useState<number>(9); // 0-indexed: 9 = October

  // Sync draft state when external value changes
  useEffect(() => {
    setDraftStart(value.startDate);
    setDraftEnd(value.endDate);
    setActivePreset(value.preset);

    if (value.endDate) {
      const parts = value.endDate.split('-');
      if (parts.length === 3) {
        setViewYear(parseInt(parts[0], 10));
        setViewMonth(parseInt(parts[1], 10) - 1);
      }
    }
  }, [value]);

  // Click outside listener to dismiss popover
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        // Revert draft changes and close
        setDraftStart(value.startDate);
        setDraftEnd(value.endDate);
        setActivePreset(value.preset);
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, value]);

  // Helper to format ISO YYYY-MM-DD
  const formatISO = (y: number, m: number, d: number) => {
    const mm = String(m + 1).padStart(2, '0');
    const dd = String(d).padStart(2, '0');
    return `${y}-${mm}-${dd}`;
  };

  const daysCount = calculateDaysBetween(draftStart, draftEnd);

  // Navigate calendar month
  const handlePrevMonth = () => {
    if (viewMonth === 0) {
      setViewYear((prev) => prev - 1);
      setViewMonth(11);
    } else {
      setViewMonth((prev) => prev - 1);
    }
  };

  const handleNextMonth = () => {
    if (viewMonth === 11) {
      setViewYear((prev) => prev + 1);
      setViewMonth(0);
    } else {
      setViewMonth((prev) => prev + 1);
    }
  };

  // Calendar matrix calculation
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
  const firstDayOfWeek = new Date(viewYear, viewMonth, 1).getDay(); // 0 is Sunday
  const monthName = new Date(viewYear, viewMonth, 1).toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
  });

  // Handle Preset Selection
  const handleSelectPreset = (presetId: string) => {
    const range = getDateRangePreset(presetId);
    setDraftStart(range.startDate);
    setDraftEnd(range.endDate);
    setActivePreset(presetId);

    // Also shift calendar view to include the range's end month
    const parts = range.endDate.split('-');
    if (parts.length === 3) {
      setViewYear(parseInt(parts[0], 10));
      setViewMonth(parseInt(parts[1], 10) - 1);
    }
  };

  // Handle Day Click
  const handleDayClick = (dayStr: string) => {
    setActivePreset(undefined); // becomes custom range

    // If both start & end exist, or no start exists, reset to click as new start
    if (draftStart && draftEnd) {
      setDraftStart(dayStr);
      setDraftEnd('');
    } else if (draftStart && !draftEnd) {
      // Second click: determine order
      if (dayStr < draftStart) {
        setDraftEnd(draftStart);
        setDraftStart(dayStr);
      } else {
        setDraftEnd(dayStr);
      }
    } else {
      setDraftStart(dayStr);
      setDraftEnd('');
    }
  };

  // Apply Changes
  const handleApply = () => {
    const finalStart = draftStart <= (draftEnd || draftStart) ? draftStart : draftEnd;
    const finalEnd = (draftEnd || draftStart) >= draftStart ? (draftEnd || draftStart) : draftStart;

    onChange({
      startDate: finalStart,
      endDate: finalEnd,
      preset: activePreset,
    });
    setIsOpen(false);
  };

  // Cancel & Close
  const handleCancel = () => {
    setDraftStart(value.startDate);
    setDraftEnd(value.endDate);
    setActivePreset(value.preset);
    setIsOpen(false);
  };

  // Reset to Default Last 7 Days
  const handleReset = () => {
    handleSelectPreset('last7days');
  };

  // Determine current active preset label for the trigger button
  const currentPresetObj = PRESET_OPTIONS.find((p) => p.id === (value.preset || ''));
  const triggerLabel = currentPresetObj
    ? currentPresetObj.label
    : formatDateRangeDisplay(value);

  const appliedDays = calculateDaysBetween(value.startDate, value.endDate);

  return (
    <div ref={containerRef} className={`relative inline-block ${className}`}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        className={`flex items-center gap-2.5 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all shadow-xs border ${
          isOpen
            ? 'bg-blue-50 dark:bg-blue-950/40 border-primary text-primary dark:text-blue-400 ring-2 ring-blue-500/20'
            : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:border-slate-300 dark:hover:border-slate-600'
        }`}
      >
        <span className="p-1 rounded-md bg-blue-100/60 dark:bg-blue-900/40 text-primary">
          <CalendarIcon className="w-3.5 h-3.5" />
        </span>
        <div className="flex flex-col text-left">
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-ink dark:text-white">{triggerLabel}</span>
            <span className="px-1.5 py-0.2 text-[10px] font-bold rounded-md bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
              {appliedDays}d
            </span>
          </div>
          <span className="text-[10px] text-muted dark:text-slate-400 font-normal">
            {formatDateRangeDisplay(value)}
          </span>
        </div>
        <ChevronDown
          className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ml-1 ${
            isOpen ? 'rotate-180 text-primary' : ''
          }`}
        />
      </button>

      {/* Popover Dropdown Panel */}
      {isOpen && (
        <div
          role="dialog"
          aria-label="Select Date Range"
          className={`absolute top-full mt-2 z-50 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xl p-4 sm:p-5 w-[92vw] max-w-[620px] max-h-[calc(100vh-140px)] overflow-y-auto motion-popover-enter ${
            align === 'right' ? 'right-0' : 'left-0'
          }`}
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/40 text-primary">
                <Clock className="w-4 h-4" />
              </span>
              <div>
                <h4 className="text-xs font-bold text-ink dark:text-white uppercase tracking-wider">
                  Filter Trend Period
                </h4>
                <p className="text-[11px] text-muted dark:text-slate-400">
                  Select a preset or choose custom start and end dates
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={handleReset}
              className="text-[11px] font-medium text-slate-500 hover:text-primary flex items-center gap-1 transition-colors"
              title="Reset to Last 7 Days"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-12 gap-4">
            {/* Left Column: Quick Presets */}
            <div className="sm:col-span-5 space-y-1 sm:border-r sm:border-slate-100 sm:dark:border-slate-800 sm:pr-4">
              <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block mb-2 px-1">
                Quick Ranges
              </span>
              <div className="space-y-1">
                {PRESET_OPTIONS.map((opt) => {
                  const isSelected = activePreset === opt.id;
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => handleSelectPreset(opt.id)}
                      className={`w-full text-left px-3 py-2 rounded-xl text-xs font-semibold flex items-center justify-between transition-all ${
                        isSelected
                          ? 'bg-blue-50 dark:bg-blue-900/30 text-primary dark:text-blue-400 font-bold'
                          : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
                      }`}
                    >
                      <div>
                        <div>{opt.label}</div>
                        <div className="text-[10px] text-muted dark:text-slate-500 font-normal">
                          {opt.description}
                        </div>
                      </div>
                      {isSelected && <Check className="w-3.5 h-3.5 text-primary shrink-0 ml-1" />}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Right Column: Interactive Calendar & Direct Inputs */}
            <div className="sm:col-span-7 flex flex-col justify-between">
              <div>
                {/* Month Navigator Header */}
                <div className="flex items-center justify-between mb-3 px-1">
                  <span className="text-xs font-bold text-ink dark:text-white">{monthName}</span>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={handlePrevMonth}
                      className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-ink transition-colors"
                      aria-label="Previous month"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      onClick={handleNextMonth}
                      className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-ink transition-colors"
                      aria-label="Next month"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Weekday Row */}
                <div className="grid grid-cols-7 gap-1 text-center mb-1">
                  {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map((d) => (
                    <span
                      key={d}
                      className="text-[10px] font-bold text-slate-400 dark:text-slate-500 py-1"
                    >
                      {d}
                    </span>
                  ))}
                </div>

                {/* Days Grid */}
                <div className="grid grid-cols-7 gap-1 text-center">
                  {/* Empty cells for month offset */}
                  {Array.from({ length: firstDayOfWeek }).map((_, i) => (
                    <div key={`empty-${i}`} className="h-7 w-7" />
                  ))}

                  {/* Day numbers */}
                  {Array.from({ length: daysInMonth }).map((_, i) => {
                    const dayNum = i + 1;
                    const dayStr = formatISO(viewYear, viewMonth, dayNum);

                    const effectiveEnd = draftEnd || (hoveredDate && hoveredDate > draftStart ? hoveredDate : draftStart);
                    const isStart = dayStr === draftStart;
                    const isEnd = dayStr === draftEnd;
                    const isInRange =
                      draftStart &&
                      effectiveEnd &&
                      dayStr > draftStart &&
                      dayStr < effectiveEnd;

                    let cellStyle =
                      'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg';

                    if (isStart && isEnd) {
                      cellStyle = 'bg-primary text-white font-bold rounded-lg shadow-xs';
                    } else if (isStart) {
                      cellStyle =
                        'bg-primary text-white font-bold rounded-l-lg rounded-r-none shadow-xs';
                    } else if (isEnd) {
                      cellStyle =
                        'bg-primary text-white font-bold rounded-r-lg rounded-l-none shadow-xs';
                    } else if (isInRange) {
                      cellStyle =
                        'bg-blue-50 dark:bg-blue-900/30 text-primary dark:text-blue-300 rounded-none font-semibold';
                    }

                    return (
                      <button
                        key={dayStr}
                        type="button"
                        onClick={() => handleDayClick(dayStr)}
                        onMouseEnter={() => setHoveredDate(dayStr)}
                        onMouseLeave={() => setHoveredDate(null)}
                        className={`h-7 w-7 text-xs flex items-center justify-center transition-all ${cellStyle}`}
                      >
                        {dayNum}
                      </button>
                    );
                  })}
                </div>

                {/* Direct Start/End Date Inputs */}
                <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase block mb-1">
                      Start Date
                    </label>
                    <input
                      type="date"
                      value={draftStart}
                      onChange={(e) => {
                        setDraftStart(e.target.value);
                        setActivePreset(undefined);
                      }}
                      className="w-full text-xs font-semibold px-2 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-ink dark:text-white focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase block mb-1">
                      End Date
                    </label>
                    <input
                      type="date"
                      value={draftEnd || draftStart}
                      onChange={(e) => {
                        setDraftEnd(e.target.value);
                        setActivePreset(undefined);
                      }}
                      className="w-full text-xs font-semibold px-2 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-ink dark:text-white focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                </div>
              </div>

              {/* Selection Summary & Action Buttons */}
              <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2">
                <div className="text-[11px] text-muted dark:text-slate-400">
                  <span>Selected: </span>
                  <span className="font-bold text-ink dark:text-white">
                    {daysCount} {daysCount === 1 ? 'day' : 'days'}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleCancel}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleApply}
                    className="px-3.5 py-1.5 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-bold shadow-xs transition-colors"
                  >
                    Apply Range
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
