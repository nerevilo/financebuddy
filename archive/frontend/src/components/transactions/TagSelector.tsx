'use client';

import { useState, useRef, useEffect } from 'react';
import { Check, Plus, ChevronDown, Tag as TagIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Tag, createTag } from '@/lib/api';
import { useTags } from '@/lib/hooks';
import { TagBadge } from '@/components/ui/TagBadge';

interface TagSelectorProps {
  selectedTagIds: string[];
  onChange: (tagIds: string[]) => void;
  className?: string;
}

export function TagSelector({ selectedTagIds, onChange, className }: TagSelectorProps) {
  const { predefinedTags, customTags, allTags, refresh } = useTags();
  const [isOpen, setIsOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newTagName, setNewTagName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedTags = allTags.filter((tag) => selectedTagIds.includes(tag.id));

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setIsCreating(false);
        setNewTagName('');
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleTag = (tagId: string) => {
    if (selectedTagIds.includes(tagId)) {
      onChange(selectedTagIds.filter((id) => id !== tagId));
    } else {
      onChange([...selectedTagIds, tagId]);
    }
  };

  const handleCreateTag = async () => {
    if (!newTagName.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const newTag = await createTag(newTagName.trim());
      await refresh();
      onChange([...selectedTagIds, newTag.id]);
      setNewTagName('');
      setIsCreating(false);
    } catch (error) {
      console.error('Failed to create tag:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div ref={dropdownRef} className={cn('relative', className)}>
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-3 py-2 border border-neutral-300 rounded-lg bg-white hover:border-neutral-400 transition-colors text-left"
      >
        <div className="flex items-center gap-2 flex-wrap min-h-[24px]">
          {selectedTags.length > 0 ? (
            selectedTags.map((tag) => (
              <TagBadge
                key={tag.id}
                tag={tag}
                size="sm"
                onRemove={() => toggleTag(tag.id)}
              />
            ))
          ) : (
            <span className="text-neutral-500 text-sm flex items-center gap-1.5">
              <TagIcon className="w-4 h-4" />
              Select tags...
            </span>
          )}
        </div>
        <ChevronDown
          className={cn(
            'w-4 h-4 text-neutral-400 transition-transform',
            isOpen && 'transform rotate-180'
          )}
        />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-50 mt-1 w-full bg-white border border-neutral-200 rounded-lg shadow-lg max-h-64 overflow-y-auto">
          {/* Predefined tags section */}
          {predefinedTags.length > 0 && (
            <>
              <div className="px-3 py-1.5 text-xs font-medium text-neutral-500 bg-cream-50 border-b border-neutral-100">
                Quick Tags
              </div>
              {predefinedTags.map((tag) => (
                <TagOption
                  key={tag.id}
                  tag={tag}
                  isSelected={selectedTagIds.includes(tag.id)}
                  onClick={() => toggleTag(tag.id)}
                />
              ))}
            </>
          )}

          {/* Custom tags section */}
          {customTags.length > 0 && (
            <>
              <div className="px-3 py-1.5 text-xs font-medium text-neutral-500 bg-cream-50 border-b border-neutral-100">
                Custom Tags
              </div>
              {customTags.map((tag) => (
                <TagOption
                  key={tag.id}
                  tag={tag}
                  isSelected={selectedTagIds.includes(tag.id)}
                  onClick={() => toggleTag(tag.id)}
                />
              ))}
            </>
          )}

          {/* Create new tag */}
          <div className="border-t border-neutral-100">
            {isCreating ? (
              <div className="p-2">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newTagName}
                    onChange={(e) => setNewTagName(e.target.value)}
                    placeholder="Tag name..."
                    className="flex-1 px-2 py-1.5 text-sm border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-400"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleCreateTag();
                      if (e.key === 'Escape') {
                        setIsCreating(false);
                        setNewTagName('');
                      }
                    }}
                  />
                  <button
                    onClick={handleCreateTag}
                    disabled={!newTagName.trim() || isSubmitting}
                    className="px-3 py-1.5 text-sm bg-primary-500 text-white rounded hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Add
                  </button>
                </div>
              </div>
            ) : (
              <button
                onClick={() => setIsCreating(true)}
                className="w-full px-3 py-2 flex items-center gap-2 text-sm text-primary-600 hover:bg-primary-50 transition-colors"
              >
                <Plus className="w-4 h-4" />
                Create new tag
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function TagOption({
  tag,
  isSelected,
  onClick,
}: {
  tag: Tag;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full px-3 py-2 flex items-center justify-between hover:bg-cream-50 transition-colors"
    >
      <div className="flex items-center gap-2">
        <span
          className="w-3 h-3 rounded-full"
          style={{ backgroundColor: tag.color || '#9CA3AF' }}
        />
        <span className="text-sm text-neutral-700">{tag.name}</span>
      </div>
      {isSelected && <Check className="w-4 h-4 text-primary-600" />}
    </button>
  );
}
