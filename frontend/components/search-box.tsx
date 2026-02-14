"use client";

import { useRef, useCallback, useState } from "react";
import { Search, Square } from "lucide-react";

interface SearchBoxProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onStop?: () => void;
  placeholder?: string;
  disabled?: boolean;
  searching?: boolean;
}

export function SearchBox({
  value,
  onChange,
  onSubmit,
  onStop,
  placeholder = "Describe who you're looking for...",
  disabled = false,
  searching = false,
}: SearchBoxProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [focused, setFocused] = useState(false);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        if (value.trim() && !disabled) onSubmit();
      }
    },
    [value, disabled, onSubmit],
  );

  return (
    <div className={focused ? "search-glow-focus" : "search-glow"}>
      <div className="relative flex items-center rounded-full border border-white/[0.08] bg-surface-search transition-colors focus-within:border-white/[0.14]">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={placeholder}
          disabled={disabled}
          className="w-full rounded-full bg-transparent px-7 py-4.5 pr-14 text-base text-text-primary placeholder:text-text-muted/70 focus:outline-none disabled:opacity-50"
        />
        {searching ? (
          <button
            type="button"
            onClick={onStop}
            className="absolute right-3.5 flex h-8 w-8 items-center justify-center rounded-full bg-white/10 hover:bg-white/20 transition-colors cursor-pointer"
            aria-label="Stop search"
          >
            <Square className="h-3.5 w-3.5 fill-text-muted text-text-muted" />
          </button>
        ) : (
          <Search className="absolute right-5 h-5 w-5 text-text-muted/60 pointer-events-none" />
        )}
      </div>
    </div>
  );
}
