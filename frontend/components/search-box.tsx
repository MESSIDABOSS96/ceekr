"use client";

import { useRef, useCallback } from "react";
import { Textarea } from "@/components/ui/textarea";
import { ArrowRight } from "lucide-react";

interface SearchBoxProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  disabled?: boolean;
}

export function SearchBox({
  value,
  onChange,
  onSubmit,
  placeholder = "Describe who you're looking for...",
  disabled = false,
}: SearchBoxProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (value.trim() && !disabled) onSubmit();
      }
    },
    [value, disabled, onSubmit],
  );

  return (
    <div className="relative rounded-3xl border border-border-subtle bg-surface transition-colors focus-within:border-twitter/30">
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={3}
        className="min-h-[68px] resize-none border-0 bg-transparent px-6 pt-5 pb-12 text-[0.95rem] text-text-primary placeholder:text-text-muted focus-visible:ring-0"
      />
      <div className="absolute right-3 bottom-3 flex items-center gap-2">
        <button
          onClick={onSubmit}
          disabled={disabled || !value.trim()}
          className="flex h-8 w-8 items-center justify-center rounded-full bg-twitter text-white transition-opacity hover:opacity-80 disabled:opacity-30"
        >
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
