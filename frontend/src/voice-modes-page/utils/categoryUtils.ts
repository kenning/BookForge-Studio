export const getCategoryColor = (category: string) => {
  const variableMap = {
    'parameter-setting': '--category-parameter-setting',
    'text-processing': '--category-text-processing',
    'audio-generation': '--category-audio-generation',
    'audio-processing': '--category-audio-processing',
    export: '--category-export',
  };

  const cssVariable = variableMap[category as keyof typeof variableMap] || '--category-default';

  // Return the CSS variable so it can be used directly in styles
  return `var(${cssVariable})`;
};

export const getCategoryIcon = (category: string) => {
  const icons = {
    'parameter-setting': '⚙️',
    'text-processing': '📝',
    'audio-generation': '🎵',
    'audio-processing': '🎛️',
    export: '📁',
  };
  return icons[category as keyof typeof icons] || '🔧';
};
