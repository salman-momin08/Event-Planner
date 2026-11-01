/**
 * Design data for the Decoration & Invitation studios: venue space presets, lighting moods,
 * invitation color themes, card layouts, occasion presets, and AI wording tones.
 * Pure data module: no DOM or network access, safe to import anywhere.
 */
export const SPACE_PRESETS = [
  ['open_garden', 'Open Garden', 'Outdoor lawn, trees, canopy & natural surroundings'],
  ['party_hall', 'Party Hall', 'Indoor banquet hall, stage, chandeliers & high ceiling'],
  ['house_room', 'House Room', 'Home living room, intimate indoor walls & cozy corners'],
  ['rooftop', 'Rooftop Terrace', 'Open-air skyline deck, pergola & string-light rails'],
  ['banquet_lawn', 'Banquet & Courtyard', 'Covered marquee tent with courtyard entryway'],
  ['other', 'Other / Custom Space', 'Specify your own unique venue or architectural space'],
];

export const LIGHTING_MOODS = [
  ['warm_ambient', 'Warm Ambient & Fairy Lights'],
  ['candlelight_intimate', 'Candlelight & Lantern Glow'],
  ['bright_festive', 'Bright Festive & Vibrant'],
  ['daylight_natural', 'Natural Daylight & Botanicals'],
  ['neon_party', 'Modern Uplighting & Party Glow'],
];

export const INVITATION_THEMES = {
  royal_indigo: {
    label: 'Royal Indigo & Gold',
    bg: '#161b33',
    innerBg: '#1e2545',
    border: '#d4af37',
    accent: '#f0c75e',
    text: '#f8f9fc',
    muted: '#c7cee3',
    motif: 'royal_lotus',
    defaults: {
      hostLine: 'TOGETHER WITH THEIR FAMILIES',
      subheadline: 'Request the honour of your presence at the royal celebration of',
      bodyText: 'Join us for an unforgettable evening of sacred traditions, music, royal dining, and joyous celebration.',
      dressCode: 'Royal Traditional / Black Tie',
    },
  },
  rose_velvet: {
    label: 'Crimson Rose & Velvet Gold',
    bg: '#380e1c',
    innerBg: '#4c1427',
    border: '#e6b86a',
    accent: '#ffd894',
    text: '#fff7f8',
    muted: '#eec6cf',
    motif: 'rose_blossom',
    defaults: {
      hostLine: 'WITH JOYFUL HEARTS & BLESSINGS',
      subheadline: 'Cordially invite you to share in the celebration of love and union',
      bodyText: 'We warmly welcome you to celebrate with us over a feast of fine cuisine, heartfelt toasts, and dancing.',
      dressCode: 'Festive Couture / Formal',
    },
  },
  botanical_sage: {
    label: 'Botanical Sage & Cream',
    bg: '#1f3328',
    innerBg: '#274033',
    border: '#a3c9a8',
    accent: '#d6eadf',
    text: '#f5fbf7',
    muted: '#c2d8c9',
    motif: 'botanical_vines',
    defaults: {
      hostLine: 'GATHER UNDER THE OPEN CANOPY',
      subheadline: 'You are warmly invited to an intimate garden celebration',
      bodyText: 'Surrounded by greenery, acoustic melodies, and seasonal fare, come celebrate this special day with us.',
      dressCode: 'Garden Chic / Linen & Pastels',
    },
  },
  sunset_terracotta: {
    label: 'Sunset Terracotta & Amber',
    bg: '#3b1d1a',
    innerBg: '#4d2622',
    border: '#f2a65a',
    accent: '#ffd29d',
    text: '#fff8f3',
    muted: '#f0cfc3',
    motif: 'sunburst_marigold',
    defaults: {
      hostLine: 'LET THE CELEBRATION BEGIN',
      subheadline: 'Join us for a vibrant evening of joy, music, and merriment',
      bodyText: 'Bring your warmest smiles and dancing shoes as we celebrate this milestone surrounded by family and friends!',
      dressCode: 'Vibrant Festive Casual',
    },
  },
  lavender_dusk: {
    label: 'Lavender Dusk & Silver Rose',
    bg: '#241b35',
    innerBg: '#312547',
    border: '#d2b7e5',
    accent: '#eed9fc',
    text: '#faf7fc',
    muted: '#cfc1de',
    motif: 'lavender_sprig',
    defaults: {
      hostLine: 'AN ENCHANTING TWILIGHT SOIREE',
      subheadline: 'We invite you to an evening under the twilight sky',
      bodyText: 'Join us as dusk falls for candlelit conversations, signature mocktails, live music, and celebration.',
      dressCode: 'Cocktail / Twilight Elegance',
    },
  },
  ocean_breeze: {
    label: 'Ocean Breeze & Pearl',
    bg: '#0f293a',
    innerBg: '#16384f',
    border: '#7cc6de',
    accent: '#b8e7f5',
    text: '#f4fbfe',
    muted: '#bad7e3',
    motif: 'coastal_palm',
    defaults: {
      hostLine: 'WELCOME TO OUR GATHERING',
      subheadline: 'Bringing together friends, family, and community',
      bodyText: 'We look forward to hosting you for a refreshing celebration filled with inspiring moments and great company.',
      dressCode: 'Smart Coastal Casual',
    },
  },
  midnight_gold: {
    label: 'Midnight Onyx & Champagne',
    bg: '#121318',
    innerBg: '#1a1c24',
    border: '#e0c088',
    accent: '#f5deb3',
    text: '#ffffff',
    muted: '#cfd3e0',
    motif: 'art_deco_fan',
    defaults: {
      hostLine: 'A STARLIGHT GALA CELEBRATION',
      subheadline: 'The pleasure of your company is requested at',
      bodyText: 'Step into an evening of timeless glamour, live entertainment, and celebratory toasts.',
      dressCode: 'Black Tie / Evening Gown',
    },
  },
  minimal_ivory: {
    label: 'Minimal Ivory & Espresso',
    bg: '#f7f3eb',
    innerBg: '#fffdf9',
    border: '#5c4738',
    accent: '#8a5a36',
    text: '#231b15',
    muted: '#5c4e43',
    motif: 'olive_branch',
    defaults: {
      hostLine: 'WARMLY HOSTED BY OUR FAMILY',
      subheadline: 'Please join us for an intimate gathering celebrating',
      bodyText: 'Your presence is the greatest gift as we gather around the table for warm conversation and celebration.',
      dressCode: 'Warm Minimal / Smart Casual',
    },
  },
};

export const INVITATION_LAYOUTS = [
  ['classic_crest', 'Classic Crest & Double Frame'],
  ['royal_mandala', 'Royal Heritage Corner Filigree'],
  ['garden_arch', 'Botanical Archway Dome'],
  ['festive_confetti', 'Celebration Starburst & Ribbon'],
  ['modern_editorial', 'Modern Editorial Minimal'],
  ['minimal_split', 'Contemporary Split Banner'],
];

export const OCCASION_DESIGN_PRESETS = [
  [
    'Wedding — Royal Crest',
    'royal_indigo',
    'classic_crest',
    {
      hostLine: 'TOGETHER WITH THEIR FAMILIES',
      subheadline: 'Request the honour of your presence at the wedding celebration of',
      bodyText: 'Join us for an unforgettable evening of sacred traditions, music, royal dining, and joyous celebration.',
      dressCode: 'Royal Traditional / Black Tie',
    },
  ],
  [
    'Wedding — Heritage Filigree',
    'rose_velvet',
    'royal_mandala',
    {
      hostLine: 'WITH JOYFUL HEARTS & FAMILY BLESSINGS',
      subheadline: 'Cordially invite you to celebrate the auspicious union of',
      bodyText: 'We warmly welcome you to celebrate with us over a feast of fine cuisine, heartfelt toasts, and Sangeet dancing.',
      dressCode: 'Festive Couture / Traditional Indian',
    },
  ],
  [
    'Garden — Botanical Arch',
    'botanical_sage',
    'garden_arch',
    {
      hostLine: 'GATHER UNDER THE OPEN CANOPY',
      subheadline: 'You are warmly invited to an intimate outdoor garden celebration',
      bodyText: 'Surrounded by greenery, acoustic melodies, and seasonal fare, come celebrate this special occasion with us.',
      dressCode: 'Garden Chic / Linen & Pastels',
    },
  ],
  [
    'Birthday — Festive Celebration',
    'sunset_terracotta',
    'festive_confetti',
    {
      hostLine: 'LET THE CELEBRATION BEGIN',
      subheadline: 'Join us for a milestone birthday celebration of joy, music, and merriment',
      bodyText: 'Bring your warmest smiles and dancing shoes as we celebrate another wonderful year surrounded by family and friends!',
      dressCode: 'Vibrant Festive Casual',
    },
  ],
  [
    'Twilight — Lavender Soiree',
    'lavender_dusk',
    'garden_arch',
    {
      hostLine: 'AN ENCHANTING TWILIGHT SOIREE',
      subheadline: 'We invite you to an evening celebration under the starlit sky',
      bodyText: 'Join us as dusk falls for candlelit conversations, signature mocktails, live acoustic music, and celebration.',
      dressCode: 'Cocktail / Twilight Elegance',
    },
  ],
  [
    'Community — Modern Editorial',
    'ocean_breeze',
    'modern_editorial',
    {
      hostLine: 'WELCOME TO OUR COMMUNITY GATHERING',
      subheadline: 'Bringing together neighbours, friends, and community members',
      bodyText: 'We look forward to hosting you for an inspiring gathering filled with meaningful connections, refreshments, and celebration.',
      dressCode: 'Smart Casual',
    },
  ],
  [
    'Gala — Midnight Champagne',
    'midnight_gold',
    'minimal_split',
    {
      hostLine: 'A STARLIGHT GALA CELEBRATION',
      subheadline: 'The pleasure of your company is requested at our evening gala',
      bodyText: 'Step into an evening of timeless glamour, live entertainment, fine dining, and celebratory toasts.',
      dressCode: 'Black Tie / Evening Attire',
    },
  ],
  [
    'Intimate — Minimal Ivory',
    'minimal_ivory',
    'classic_crest',
    {
      hostLine: 'WARMLY HOSTED BY OUR FAMILY',
      subheadline: 'Please join us for an intimate family gathering celebrating',
      bodyText: 'Your presence is our greatest joy as we gather around the table for warm conversation, dinner, and celebration.',
      dressCode: 'Warm Minimal / Smart Casual',
    },
  ],
];

export const INVITATION_TONES = [
  ['warm_traditional', 'Warm & Heartfelt'],
  ['modern_minimal', 'Crisp & Modern'],
  ['playful_celebration', 'Joyful & Festive'],
  ['formal_black_tie', 'Formal & Elegant'],
];
