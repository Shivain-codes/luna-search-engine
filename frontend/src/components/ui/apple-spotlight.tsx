'use client';

import { cn } from '@/lib/utils';
import { api } from '@/services/api';

import { AnimatePresence, motion } from 'framer-motion';
import {
  Activity,
  ChevronRight,
  Files,
  Folder,
  Globe,
  LayoutGrid,
  Search,
} from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';

interface Shortcut {
  label: string;
  icon: React.ReactNode;
  link: string;
}

interface SearchResult {
  icon: React.ReactNode;
  label: string;
  description: string;
  link: string;
}

const SVGFilter = () => {
  return (
    <svg width="0" height="0">
      <filter id="blob">
        <feGaussianBlur stdDeviation="10" in="SourceGraphic" />
        <feColorMatrix
          values="
      1 0 0 0 0
      0 1 0 0 0
      0 0 1 0 0
      0 0 0 18 -9
    "
          result="blob"
        />
        <feBlend in="SourceGraphic" in2="blob" />
      </filter>
    </svg>
  );
};

interface ShortcutButtonProps {
  icon: React.ReactNode;
  link: string;
}

const ShortcutButton = ({ icon, link }: ShortcutButtonProps) => {
  return (
    <a href={link} target="_blank">
      <div className="rounded-full cursor-pointer hover:shadow-lg opacity-30 hover:opacity-100 transition-[opacity,shadow] duration-200">
        <div className="size-16 aspect-square flex items-center justify-center">{icon}</div>
      </div>
    </a>
  );
};

interface SpotlightPlaceholderProps {
  text: string;
  className?: string;
}

const SpotlightPlaceholder = ({ text, className }: SpotlightPlaceholderProps) => {
  return (
    <motion.div
      layout
      className={cn('absolute text-gray-500 flex items-center pointer-events-none z-10', className)}
    >
      <AnimatePresence mode="popLayout">
        <motion.p
          layoutId={`placeholder-${text}`}
          key={`placeholder-${text}`}
          initial={{ opacity: 0, y: 10, filter: 'blur(5px)' }}
          animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
          exit={{ opacity: 0, y: -10, filter: 'blur(5px)' }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
        >
          {text}
        </motion.p>
      </AnimatePresence>
    </motion.div>
  );
};

interface SpotlightInputProps {
  placeholder: string;
  hidePlaceholder: boolean;
  value: string;
  onChange: (value: string) => void;
  onKeyDown?: (e: React.KeyboardEvent) => void;
  placeholderClassName?: string;
}

const SpotlightInput = ({
  placeholder,
  hidePlaceholder,
  value,
  onChange,
  onKeyDown,
  placeholderClassName
}: SpotlightInputProps) => {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  return (
    <div className="flex items-center w-full justify-start gap-2 px-6 h-16">
      <motion.div layoutId="search-icon" className="text-accent-500">
        <Search />
      </motion.div>
      <div className="flex-1 relative text-2xl">
        {!hidePlaceholder && (
          <SpotlightPlaceholder text={placeholder} className={placeholderClassName} />
        )}

        <motion.input
          ref={inputRef}
          layout="position"
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          className="w-full bg-transparent outline-none ring-none placeholder:text-primary-400"
        />
      </div>
    </div>
  );
};

interface SearchResultCardProps extends SearchResult {
  isLast: boolean;
}

const SearchResultCard = ({ icon, label, description, link, isLast }: SearchResultCardProps) => {
  return (
    <a href={link} target="_blank" className="overflow-hidden w-full group/card">
      <div
        className={cn(
          'flex items-center text-primary-900 dark:text-primary-50 justify-start hover:bg-white/50 dark:hover:bg-white/10 gap-3 py-2 px-2 rounded-xl hover:shadow-sm w-full transition-all duration-200',
          isLast && 'rounded-b-3xl'
        )}
      >
        <div className="size-8 [&_svg]:stroke-[1.5] [&_svg]:size-6 aspect-square flex items-center justify-center text-accent-500">
          {icon}
        </div>
        <div className="flex flex-col">
          <p className="font-medium">{label}</p>
          <p className="text-xs opacity-50">{description}</p>
        </div>
        <div className="flex-1 flex items-center justify-end opacity-0 group-hover/card:opacity-100 transition-opacity duration-200">
          <ChevronRight className="size-6 text-accent-500" />
        </div>
      </div>
    </a>
  );
};

interface SearchResultsContainerProps {
  searchResults: SearchResult[];
  onHover: (index: number | null) => void;
}

const SearchResultsContainer = ({ searchResults, onHover }: SearchResultsContainerProps) => {
  return (
    <motion.div
      layout
      onMouseLeave={() => onHover(null)}
      className="px-2 border-t border-primary-200 dark:border-primary-800 flex flex-col bg-white/50 dark:bg-black/50 backdrop-blur-md max-h-96 overflow-y-auto w-full py-2"
    >
      {searchResults.map((result, index) => {
        return (
          <motion.div
            key={`search-result-${index}`}
            onMouseEnter={() => onHover(index)}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 10 }}
            transition={{
              delay: index * 0.05,
              duration: 0.2,
              ease: 'easeOut'
            }}
          >
            <SearchResultCard
              icon={result.icon}
              label={result.label}
              description={result.description}
              link={result.link}
              isLast={index === searchResults.length - 1}
            />
          </motion.div>
        );
      })}
    </motion.div>
  );
};

interface AppleSpotlightProps {
  shortcuts?: Shortcut[];
  isOpen?: boolean;
  handleClose?: () => void;
  onSearch?: (value: string) => void;
}

const AppleSpotlight = ({
  shortcuts = [
    {
      label: 'Apps',
      icon: <LayoutGrid />,
      link: '/docs/components'
    },
    {
      label: 'Files',
      icon: <Folder />,
      link: '/docs/texts'
    },
    {
      label: 'Actions',
      icon: <Activity />,
      link: '/docs/buttons'
    },
    {
      label: 'Clipboard',
      icon: <Files />,
      link: '/docs/backgrounds'
    }
  ],
  isOpen = true,
  handleClose = () => {},
  onSearch
}: AppleSpotlightProps) => {
  const [hovered, setHovered] = useState(false);
  const [hoveredSearchResult, setHoveredSearchResult] = useState<number | null>(null);
  const [hoveredShortcut, setHoveredShortcut] = useState<number | null>(null);
  const [searchValue, setSearchValue] = useState('');
  const [suggestions, setSuggestions] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (searchValue.length < 2) {
        setSuggestions([]);
        return;
      }

      setIsLoading(true);
      try {
        const response = await api.suggest(searchValue);
        // Map SuggestResponse to SearchResult
        const suggestionsList = response?.suggestions || [];
        const mapped = suggestionsList.map(s => ({
          icon: <Globe />, // Default icon for suggestions
          label: s.text,
          description: s.description || 'Suggested result',
          link: `/search?q=${encodeURIComponent(s.text)}`
        }));
        setSuggestions(mapped);
      } catch (error) {
        console.error('Failed to fetch suggestions:', error);
        setSuggestions([]);
      } finally {
        setIsLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchValue]);

  const handleSearchValueChange = (value: string) => {
    setSearchValue(value);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (hoveredSearchResult !== null && suggestions[hoveredSearchResult]) {
        const selected = suggestions[hoveredSearchResult];
        onSearch?.(selected.label);
      } else if (searchValue) {
        onSearch?.(searchValue);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHoveredSearchResult(prev => (prev === null || prev >= suggestions.length - 1 ? 0 : prev + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHoveredSearchResult(prev => (prev === null || prev <= 0 ? suggestions.length - 1 : prev - 1));
    }
  };

  return (
    <AnimatePresence mode="wait">
      {isOpen && (
        <motion.div
          initial={{
            opacity: 0,
            filter: 'blur(20px) url(#blob)',
            scaleX: 1.3,
            scaleY: 1.1,
            y: -10
          }}
          animate={{
            opacity: 1,
            filter: 'blur(0px) url(#blob)',
            scaleX: 1,
            scaleY: 1,
            y: 0
          }}
          exit={{
            opacity: 0,
            filter: 'blur(20px) url(#blob)',
            scaleX: 1.3,
            scaleY: 1.1,
            y: 10
          }}
          transition={{
            stiffness: 550,
            damping: 50,
            type: 'spring'
          }}
          className="fixed inset-0 z-50 flex flex-col items-center justify-center"
          onClick={handleClose}
        >
          <SVGFilter />

          <div
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => {
              setHovered(false);
              setHoveredShortcut(null);
            }}
            onClick={(e) => e.stopPropagation()}
            style={{ filter: 'url(#blob)' }}
            className={cn(
              'w-full flex items-center justify-end gap-4 z-20 group',
              '[&>div]:bg-white/70 dark:bg-black/70 [&>div]:text-primary-900 dark:text-primary-50 [&>div]:rounded-full [&>div]:backdrop-blur-xl',
              '[&_svg]:size-7 [&_svg]:stroke-[1.4]',
              'max-w-3xl'
            )}
          >
            <AnimatePresence mode="popLayout">
              <motion.div
                layoutId="search-input-container"
                transition={{
                  layout: {
                    duration: 0.5,
                    type: 'spring',
                    bounce: 0.2
                  }
                }}
                style={{
                  borderRadius: '30px'
                }}
                                  className="h-full w-full flex flex-col items-center justify-start z-10 relative shadow-2xl overflow-hidden border border-primary-200 dark:border-primary-800 glass"
              >
                <SpotlightInput
                  placeholder={
                    hoveredShortcut !== null
                      ? shortcuts[hoveredShortcut].label
                      : hoveredSearchResult !== null
                      ? suggestions[hoveredSearchResult]?.label || 'Search'
                      : 'Search'
                  }
                  placeholderClassName={
                    hoveredSearchResult !== null ? 'text-black bg-white' : 'text-gray-500'
                  }
                  hidePlaceholder={!(hoveredSearchResult !== null || !searchValue)}
                  value={searchValue}
                  onChange={handleSearchValueChange}
                  onKeyDown={handleKeyDown}
                />

                {isLoading && (
                  <div className="absolute bottom-2 right-6 text-xs text-gray-400 animate-pulse">
                    Searching...
                  </div>
                )}

                {searchValue && (
                  <SearchResultsContainer
                    searchResults={suggestions}
                    onHover={setHoveredSearchResult}
                  />
                )}
              </motion.div>
              {hovered &&
                !searchValue &&
                shortcuts.map((shortcut, index) => (
                  <motion.div
                    key={`shortcut-${index}`}
                    onMouseEnter={() => setHoveredShortcut(index)}
                    layout
                    initial={{ scale: 0.7, x: -1 * (64 * (index + 1)) }}
                    animate={{ scale: 1, x: 0 }}
                    exit={{
                      scale: 0.7,
                      x:
                        1 *
                        (16 * (shortcuts.length - index - 1) + 64 * (shortcuts.length - index - 1))
                    }}
                    transition={{
                      duration: 0.8,
                      type: 'spring',
                      bounce: 0.2,
                      delay: index * 0.05
                    }}
                    className="rounded-full cursor-pointer"
                  >
                    <ShortcutButton icon={shortcut.icon} link={shortcut.link} />
                  </motion.div>
                ))}
            </AnimatePresence>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export { AppleSpotlight };
