# Harington Design System — OmnIA v1.0

> Document de référence pour toute implémentation frontend OmnIA.
> Police : Roboto. Framework : React + TypeScript + Tailwind CSS + shadcn/ui.

---

## 1. Palette de couleurs

### Couleurs principales

| Token | Hex | Usage | Tailwind |
|-------|-----|-------|----------|
| **Navy** | `#0F1D33` | Headers, sidebar, tabs actifs, titres, logo | `bg-[#0F1D33]` `text-[#0F1D33]` |
| **Navy Mid** | `#1B2A4A` | Hover sidebar, sous-headers | `bg-[#1B2A4A]` |
| **Navy Light** | `#354A6B` | Texte secondaire nav, timestamps, labels | `text-[#354A6B]` |
| **Teal** | `#AABFC2` | Accent, dividers, sous-titres header | `text-[#AABFC2]` |
| **Background** | `#EFF1F5` | Fond principal de l'application | `bg-[#EFF1F5]` |
| **Background Alt** | `#E4E6EC` | Fond inputs, hover states, fond alternatif | `bg-[#E4E6EC]` |
| **Divider** | `#D5D8DE` | Borders, séparateurs, contours de cards | `border-[#D5D8DE]` |
| **White** | `#FFFFFF` | Cards, conteneurs, fond de tabs | `bg-white` |

### Couleurs sémantiques

| Token | Hex | Fond | Usage |
|-------|-----|------|-------|
| **Blue** | `#1D4ED8` | `#EFF6FF` | Liens, actions, badges MCP, niveau "Interne" |
| **Green** | `#0B7A3E` | `#E6F4EE` | Succès, validation, niveau "Public" |
| **Orange** | `#B45309` | `#FEF3C7` | Warning, modéré, niveau "Confidentiel" |
| **Red** | `#B91C1C` | `#FEE2E2` | Erreur, critique, niveau "Secret" |
| **Grey** | `#4A5568` | — | Corps de texte, descriptions |
| **Muted** | `#A0ABBD` | — | Métadonnées tertiaires, timestamps légers |

### Badges de capacités (uniformes partout)

| Type | Background | Texte | Bordure | Tailwind |
|------|-----------|-------|---------|----------|
| **Skills** | `#FDF2F8` | `#BE185D` | `#FBCFE8` | `bg-[#FDF2F8] text-[#BE185D] border-[#FBCFE8]` |
| **MCP** | `#F5F3FF` | `#6D28D9` | `#DDD6FE` | `bg-[#F5F3FF] text-[#6D28D9] border-[#DDD6FE]` |
| **Tools** | `#ECFDF5` | `#047857` | `#A7F3D0` | `bg-[#ECFDF5] text-[#047857] border-[#A7F3D0]` |

### Badges de confidentialité

| Niveau | Background | Texte | Bordure | Sémantique |
|--------|-----------|-------|---------|------------|
| **Public** | `#E6F4EE` | `#0B7A3E` | `#0B7A3E30` | Accessible à tous |
| **Interne** | `#EFF6FF` | `#1D4ED8` | `#1D4ED830` | Collaborateurs authentifiés |
| **Confidentiel** | `#FEF3C7` | `#B45309` | `#B4530930` | Équipe restreinte |
| **Secret** | `#FEE2E2` | `#B91C1C` | `#B91C1C30` | Accès nominatif |

---

## 2. Typographie

### Police

```css
font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
```

Import Google Fonts :
```css
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap');
```

### Corps de base

```css
body {
  font-size: 17px;
  line-height: 1.5;
  font-weight: 400;
  color: #0F1D33;
  -webkit-font-smoothing: antialiased;
}
```

### Échelle de poids

| Poids | Token | Usage |
|-------|-------|-------|
| **900 (Black)** | `font-black` | Titres de pages, KPI numbers, logo "OmnIA" |
| **700 (Bold)** | `font-bold` | Headers sections, noms agents, tabs actifs, boutons primaires |
| **500 (Medium)** | `font-medium` | Labels de formulaires, boutons secondaires |
| **400 (Normal)** | `font-normal` | Corps de texte, descriptions, tabs inactifs |
| **300 (Light)** | `font-light` | Timestamps, métadonnées secondaires |

### Échelle de tailles

| Size | Usage |
|------|-------|
| `text-[22px]` | Titres de pages dans les headers navy |
| `text-[20px]` | SectionH2, titres de sections internes |
| `text-[18px]` | Logo "OmnIA" dans la sidebar |
| `text-[16px]` | StatBox KPI numbers |
| `text-[15px]` | Onglets actifs dans les tab bars |
| `text-[14px]` | Titres de conversations sidebar, headers de cards |
| `text-[13px]` | Onglets inactifs, items de menu sidebar |
| `text-[12px]` | Métadonnées sidebar, sous-titres headers, badges |
| `text-[11px]` | Tags (MetaTag, capability badges) |
| `text-[10px]` | Statistiques très compactes, compteurs de filtres |
| `text-[9px]` | Labels StatBox, micro-texte uppercase |

---

## 3. Espacements & Rayons

### Border-radius par contexte

| Radius | Usage |
|--------|-------|
| `rounded-[10px]` | Conteneur de tab bar |
| `rounded-[8px]` | Cards principales, conteneurs de contenu |
| `rounded-[6px]` | Boutons, tabs individuels, StatBox |
| `rounded-[4px]` | Badges HlBadge |
| `rounded-[3px]` | Tags MetaTag/TblBadge, micro-badges |
| `rounded-full` | Dots, avatars, indicateurs ronds |

### Paddings standards

| Pattern | Usage |
|---------|-------|
| `px-[28px] py-[18px]` | Headers de pages navy |
| `px-[28px] pt-4` | Zone de tab bar |
| `p-5` ou `p-6` | Contenu de cards |
| `px-4 py-3` | Cellules de tableau |
| `px-3.5 py-2` | StatBox |
| `px-2.5 py-1` | Badges HlBadge |
| `px-2 py-[2px]` | Micro-badges, tags |

### Ombres

| Token | CSS | Usage |
|-------|-----|-------|
| Card shadow | `shadow-sm` ou aucune | Cards standards |
| Tab active | `shadow-sm` | Tab sélectionné |
| Hover card | `shadow-[0_4px_16px_rgba(15,29,51,0.06)]` | Card au hover |
| Accessibility bar | `shadow-[0_4px_16px_rgba(15,29,51,0.08)]` | Barre flottante |

---

## 4. Composants primitifs

### StatBox — KPI dans les headers navy

```tsx
const StatBox = ({num, label}: {num: string; label: string}) => (
  <div className="bg-white/10 border border-white/15 rounded-[6px] px-3.5 py-2 text-center min-w-[64px]">
    <div className="text-[16px] font-black leading-none text-white">{num}</div>
    <div className="text-[9px] font-medium uppercase tracking-[0.04em] text-white/60 mt-[3px]">{label}</div>
  </div>
);
```

### HlBadge — Badge coloré (5 variants)

```tsx
const HlBadge = ({children, variant}: {children: React.ReactNode; variant: string}) => {
  const s: Record<string, string> = {
    urgent:   "bg-[#FEE2E2] text-[#B91C1C]",
    deadline: "bg-[#FEF3C7] text-[#B45309]",
    budget:   "bg-[#E6F4EE] text-[#0B7A3E]",
    idf:      "bg-[#EFF6FF] text-[#1D4ED8]",
    region:   "bg-[#E4E6EC] text-[#0F1D33]",
  };
  return (
    <span className={`inline-flex items-center text-[12px] font-semibold px-2.5 py-1 rounded-[4px] ${s[variant] || s.region}`}>
      {children}
    </span>
  );
};
```

### TblBadge — Badge compact tableau

```tsx
const TblBadge = ({children, variant}: {children: React.ReactNode; variant: "high" | "low"}) => (
  <span className={`inline-flex items-center text-[11px] font-semibold px-[7px] py-[2px] rounded-[3px] whitespace-nowrap ${
    variant === "high" ? "bg-[#FEF3C7] text-[#B45309]" : "bg-[#E4E6EC] text-[#4A5568]"
  }`}>
    {children}
  </span>
);
```

### MetaTag — Tag skill (rose pastel)

```tsx
const MetaTag = ({children}: {children: React.ReactNode}) => (
  <span className="inline-flex items-center bg-[#FDF2F8] text-[#BE185D] text-[11px] font-medium px-2 py-[2px] rounded-[3px] border border-[#FBCFE8]">
    {children}
  </span>
);
```

### CountBadge — Compteur arrondi

```tsx
const CountBadge = ({children}: {children: React.ReactNode}) => (
  <span className="bg-[#D8DCE3] text-[#0F1D33] text-[11px] font-semibold px-2 py-[2px] rounded-[10px]">
    {children}
  </span>
);
```

### ScoreCircle — Note /5

```tsx
const ScoreCircle = ({score}: {score: number}) => {
  const bg = score >= 5 ? "bg-[#0B7A3E]"
           : score >= 4 ? "bg-[#1D6FA4]"
           : score >= 3 ? "bg-[#B45309]"
           : "bg-[#6B7280]";
  return (
    <div className={`w-10 h-10 rounded-full ${bg} text-white text-[14px] font-bold flex items-center justify-center shrink-0`}>
      {score.toFixed(1)}
    </div>
  );
};
```

### SectionH2 — Titre de section avec bordure

```tsx
const SectionH2 = ({children, badge}: {children: React.ReactNode; badge?: React.ReactNode}) => (
  <h2 className="text-[20px] font-normal text-[#0F1D33] pb-2 mb-3.5 border-b-2 border-[#0F1D33] flex items-center gap-2.5">
    {children}
    {badge && <span className="text-[12px] font-medium text-[#4A5568]">{badge}</span>}
  </h2>
);
```

### Ic — Wrapper emoji bleu-gris

```tsx
const Ic = ({children, s}: {children: React.ReactNode; s?: number}) => (
  <span className="ic-muted inline-flex" style={s ? {fontSize: s} : undefined}>
    {children}
  </span>
);
```

---

## 5. Système d'icônes

### Icônes SVG sidebar

Toutes les icônes du menu sont des SVG inline avec `stroke="currentColor"`, `strokeWidth="1.8"`, taille 18×18.

### Icônes emoji — Système ic-muted / ic-active

```css
.ic-muted {
  filter: grayscale(80%) sepia(20%) saturate(150%) hue-rotate(180deg) brightness(0.65);
  opacity: 0.85;
}
.ic-active {
  filter: none;
  opacity: 1;
}
```

**Règles :**
- Toutes les icônes emoji sont `ic-muted` par défaut
- Deviennent `ic-active` uniquement quand leur élément parent est **sélectionné**
- Les emojis **sémantiques** gardent toujours leurs couleurs : 🚫 ⚠️ ✅ ❌

---

## 6. Patterns de mise en page

### Header de page (navy)

```tsx
<div className="bg-[#0F1D33] px-[28px] py-[18px]">
  <div className="flex items-start justify-between gap-6">
    <div>
      <div className="text-[22px] font-black text-white tracking-[-0.5px]">Titre</div>
      <div className="text-[12px] font-light text-white/60 mt-[2px]">Sous-titre</div>
    </div>
    <div className="flex items-center gap-2 shrink-0">
      <StatBox num="42" label="Total"/>
    </div>
  </div>
</div>
```

### Tab bar

```tsx
<div className="px-[28px] pt-4">
  <div className="bg-white rounded-[10px] border border-[#D5D8DE] p-[4px] inline-flex gap-[2px] shadow-sm">
    {tabs.map(t => (
      <button
        key={t.id}
        onClick={() => setTab(t.id)}
        className={`px-4 py-[9px] rounded-[6px] transition-all flex items-center gap-2
          ${tab === t.id
            ? "text-[15px] font-bold bg-[#0F1D33] text-white shadow-sm"
            : "text-[13px] font-normal text-[#4A5568] hover:bg-[#EFF1F5] hover:text-[#0F1D33]"
          }`}
      >
        <span className={tab === t.id ? "ic-active" : "ic-muted"}>{t.ic}</span>
        {t.label}
      </button>
    ))}
  </div>
</div>
```

**IMPORTANT** : même `py-[9px]` sur actif ET inactif — empêche le tremblement au changement d'onglet.

### Card de contenu

```tsx
<div className="bg-white rounded-[8px] border border-[#D5D8DE] overflow-hidden">
  <div className="bg-[#0F1D33] px-4 py-2.5">
    <span className="text-[14px] font-bold text-white tracking-[-0.1px]">Titre section</span>
  </div>
  <div className="p-5">...</div>
</div>
```

### Tableau (header navy)

```tsx
<table className="w-full border-collapse">
  <thead>
    <tr className="bg-[#0F1D33]">
      <th className="text-left text-[12px] font-bold text-white uppercase tracking-[0.04em] px-4 py-3">Col</th>
    </tr>
  </thead>
  <tbody>
    <tr className="border-b border-[#D5D8DE] last:border-0 hover:bg-[#F4F5F8] transition-colors">
      <td className="px-4 py-3 text-[13px] text-[#0F1D33]">...</td>
    </tr>
  </tbody>
</table>
```

### Barre d'action sticky

```tsx
<div className="shrink-0 border-t border-[#D5D8DE] bg-white px-[28px] py-3 flex items-center justify-between">
  <div className="text-[12px] text-[#A0ABBD] font-light">Message contextuel</div>
  <div className="flex items-center gap-2">
    <button className="h-[38px] px-5 rounded-[6px] border border-[#D5D8DE] bg-white text-[#354A6B] text-[13px] font-medium">
      Secondaire
    </button>
    <button className="h-[38px] px-6 rounded-[6px] bg-[#0F1D33] text-white text-[14px] font-bold">
      Action principale
    </button>
  </div>
</div>
```

---

## 7. CSS Global (index.css)

```css
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --navy: #0F1D33;
    --navy-mid: #1B2A4A;
    --navy-light: #354A6B;
    --bg: #EFF1F5;
    --bg-alt: #E4E6EC;
    --divider: #D5D8DE;
    --green: #0B7A3E;
    --green-bg: #E6F4EE;
    --orange: #B45309;
    --orange-bg: #FEF3C7;
    --red: #B91C1C;
    --red-bg: #FEE2E2;
    --blue: #1D4ED8;
    --blue-bg: #EFF6FF;
  }
}

@layer base {
  * { box-sizing: border-box; }
  body {
    font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    font-weight: 400;
    background: #EFF1F5;
    color: #0F1D33;
    font-size: 17px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }
}

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #EFF1F5; }
::-webkit-scrollbar-thumb { background: #D5D8DE; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #354A6B; }

.ic-muted {
  filter: grayscale(80%) sepia(20%) saturate(150%) hue-rotate(180deg) brightness(0.65);
  opacity: 0.85;
}
.ic-active { filter: none; opacity: 1; }
```

---

## 8. États interactifs

### Hover

| Contexte | Normal | Hover |
|----------|--------|-------|
| Card | `border-[#D5D8DE]` | `shadow-[0_4px_16px_rgba(15,29,51,0.06)]` |
| Sidebar item | `text-[#354A6B]` | `text-[#0F1D33] bg-[#EFF1F5]` |
| Tab inactif | `text-[#4A5568]` | `bg-[#EFF1F5] text-[#0F1D33]` |
| Bouton navy | `bg-[#0F1D33]` | `bg-[#1B2A4A]` |

### Sélection

| Contexte | Non sélectionné | Sélectionné |
|----------|-----------------|-------------|
| Tab | `text-[13px] font-normal text-[#4A5568]` | `text-[15px] font-bold bg-[#0F1D33] text-white shadow-sm` |
| Sidebar item | `text-[#354A6B]` | `bg-[#0F1D33] text-white` |
| Icône emoji | `ic-muted` | `ic-active` |

---

## 9. Logo OmnIA

```tsx
<svg viewBox="0 0 32 32" fill="none" width="28" height="28">
  <rect x="2"  y="14" width="28" height="4" rx="1" fill="#AABFC2" opacity="0.6"/>
  <rect x="6"  y="8"  width="20" height="4" rx="1" fill="#AABFC2" opacity="0.8"/>
  <rect x="10" y="2"  width="12" height="4" rx="1" fill="#AABFC2"/>
  <rect x="4"  y="20" width="24" height="4" rx="1" fill="#AABFC2" opacity="0.4"/>
  <rect x="8"  y="26" width="16" height="4" rx="1" fill="#AABFC2" opacity="0.2"/>
</svg>
<span className="text-[18px] font-black text-white tracking-[-0.3px]">OmnIA</span>
```

---

## 10. Badges Fleet — Composants spécifiques

```tsx
const IdentityBadge = ({mode}: {mode: "claws" | "assistant"}) => (
  <span className={`inline-flex items-center text-[11px] font-medium px-2 py-[2px] rounded-[3px] border ${
    mode === "claws"
      ? "bg-[#FEF3C7] text-[#B45309] border-[#F59E0B30]"
      : "bg-[#EFF6FF] text-[#1D4ED8] border-[#1D4ED830]"
  }`}>
    {mode === "claws" ? "🔧 Claws" : "🤖 Assistant"}
  </span>
);

const PermBadge = ({level}: {level: "edit" | "run" | "clone"}) => {
  const styles = {
    edit:  "bg-[#FEE2E2] text-[#B91C1C]",
    run:   "bg-[#E6F4EE] text-[#0B7A3E]",
    clone: "bg-[#F5F3FF] text-[#6D28D9]",
  };
  return (
    <span className={`inline-flex items-center text-[11px] font-semibold px-2 py-[2px] rounded-[3px] ${styles[level]}`}>
      {level}
    </span>
  );
};

const InboxStatusBadge = ({status}: {status: "pending" | "approved" | "rejected"}) => {
  const styles = {
    pending:  "bg-[#FEF3C7] text-[#B45309]",
    approved: "bg-[#E6F4EE] text-[#0B7A3E]",
    rejected: "bg-[#FEE2E2] text-[#B91C1C]",
  };
  return (
    <span className={`inline-flex items-center text-[11px] font-semibold px-2 py-[2px] rounded-[3px] ${styles[status]}`}>
      {status === "pending" ? "⏳ En attente" : status === "approved" ? "✅ Approuvé" : "❌ Rejeté"}
    </span>
  );
};
```
