# Ingredient Dictionary — Singapore Home Chef

Localized bilingual dictionary for the ~20 ingredients you will encounter in a Singaporean home kitchen. Each entry has the **English name**, the **Malay/Tamil name** (the wet-market vendor will say this), the **Chinese name** (the supermarket label will say this), the **supermarket SKU shape** (what to look for on the shelf at NTUC / Sheng Siong / Cold Storage), and the **wet-market vendor request** (what to say at Tekka / Tiong Bahru / Geylang Serai).

## How to use this dictionary

1. **You are at the supermarket.** Read the `supermarket_sku` column. It tells you the *brand + size* to look for (e.g. "Tai Hua dark soy 640ml", "Prima Taste sambal 240g").
2. **You are at the wet market.** Read the `wet_market_request` column. It tells you the *conversational sentence* to say to the vendor (e.g. "Beri saya 200g bawang merah, 100g bawang putih, 5 batang serai").
3. **You don't know the English name.** Read the `malay` / `chinese` columns. The vendor will recognise these first.
4. **The ingredient is in a recipe you don't have.** Read `common_substitutes`. It tells you what to use if the named ingredient is sold out / out of season / too expensive.

## The dictionary

### Aromatics

| English          | Malay / regional | 中文 (Chinese)        | Supermarket SKU                                  | Wet-market request                              | Common substitutes                          | Dietary flags |
| ---------------- | ---------------- | --------------------- | ------------------------------------------------ | ----------------------------------------------- | ------------------------------------------- | ------------- |
| **Shallot**      | Bawang merah     | 红葱头                 | Red shallots 200g bag (S$2–3)                     | "Beri saya 200g bawang merah"                  | Pearl onions, French shallots (3× price)    | vegan, halal  |
| **Garlic**       | Bawang putih     | 蒜头                   | China / India garlic 200g (S$1.50–2)              | "Bawang putih 200g"                             | Pre-minced jar (lazy; 50% flavour loss)     | vegan, halal  |
| **Ginger**       | Halia            | 姜                    | Local ginger 200g (S$2–3)                        | "Halia tua 200g, jangan terlalu muda"           | Galangal (different flavour, not 1:1)       | vegan, halal  |
| **Galangal**     | Lengkuas         | 南姜 / 蓝姜             | Lengkuas 100g (S$2) — sometimes labelled "blue ginger" | "Lengkuas 100g"                                 | Ginger + 1/4 tsp white pepper (imperfect)    | vegan, halal  |
| **Lemongrass**   | Serai            | 香茅                   | Pre-chopped serai 100g or whole stalks 100g     | "Serai 5 batang, pilih yang tua"                | Lemon zest + 1 tsp lime juice (imperfect)   | vegan, halal  |
| **Turmeric**     | Kunyit           | 姜黄                   | Fresh turmeric root 100g (S$2) or powder 50g jar  | "Kunyit hidup 100g"                             | Turmeric powder 1 tsp = 1 inch fresh         | vegan, halal  |
| **Candlenut**    | Buah keras       | Kemiri                 | Kemiri 100g jar (S$3) or vacuum-packed          | "Buah keras 50g"                                | Macadamia (1:1) or cashew (1:1, slightly sweet) | vegan, halal  |

### Pastes, condiments, sauces

| English          | Malay / regional | 中文 (Chinese)        | Supermarket SKU                                  | Wet-market request                              | Common substitutes                          | Dietary flags |
| ---------------- | ---------------- | --------------------- | ------------------------------------------------ | ----------------------------------------------- | ------------------------------------------- | ------------- |
| **Belacan**      | Belacan          | 虾酱 / 虾膏              | "Prawn Paste" 100g tub (e.g. BABA's)             | "Belacan satu ketul, bakar dulu" (toast first)  | Thai *kapi* (different profile, ok 1:1)     | halal ¹       |
| **Dark soy**     | Kicap pekat      | 老抽                   | Tai Hua dark soy 640ml (S$4) — the SG standard  | n/a — supermarkets only                          | Light soy + 1 tsp molasses (imperfect)      | vegan ²       |
| **Light soy**    | Kicap cair       | 生抽                   | Tai Hua light soy 640ml (S$3.50)                | n/a — supermarkets only                          | Japanese kikkoman (1:1, saltier)            | vegan, halal  |
| **Fish sauce**   | Kicap ikan       | 鱼露                   | Tiparos 700ml (S$4) or Thai Kitchen              | n/a — supermarkets only                          | Soy sauce + 1 tsp anchovy (not vegan)       | halal ²       |
| **Sambal paste** | Sambal           | 辣椒酱                  | Prima Taste / Tean's / Ponniah 240g jar         | "Sambal tumis 200g" (pre-cooked paste)           | Bird's eye chilli + garlic + belacan (DIY)  | vegan ³, halal |
| **Shaoxing wine**| Shaoxing jiu     | 绍兴酒                  | Pagoda Shaoxing 640ml (S$5) — look for 绍兴花雕  | n/a — supermarkets only                          | Dry sherry (1:1) or mirin (sweeter, use less) | vegan, halal  |

¹ Belacan is halal if the brand certifies it (most supermarket brands do). Wet-market belacan is often non-halal — ask the vendor for *belacan halal* or buy from the certified shelf at NTUC.

² Dark soy and fish sauce are *technically* vegan / halal at the supermarket, but a strict Muslim vegetarian may want a halal-certified brand. The 3 flags cover the *default* case.

³ Sambal paste is *vegan* if the recipe does not include *belacan* (shrimp paste). Most supermarket brands include it; read the label. The S$4 Prima Taste packet is vegan; the S$3 house brand may not be.

### Vegetables

| English          | Malay / regional | 中文 (Chinese)        | Supermarket SKU                                  | Wet-market request                              | Common substitutes                          | Dietary flags |
| ---------------- | ---------------- | --------------------- | ------------------------------------------------ | ----------------------------------------------- | ------------------------------------------- | ------------- |
| **Kangkung**     | Kangkung / bayam | 空心菜 / 通菜            | Pre-washed 200g bag (S$2.50) or whole 500g bunch | "Kangkung satu ikat, pilih yang muda"           | Spinach (wetter, milder, 1:1)               | vegan, halal  |
| **Calamansi**    | Limau kasturi    | 桔子 / 酸柑              | Bottled juice 250ml (S$3) — *avoid*; always buy fresh | "Limau kasturi 200g" (sold by weight, not by piece) | Lime + 1 tsp sugar (imperfect)              | vegan, halal  |

### Proteins

| English          | Malay / regional | 中文 (Chinese)        | Supermarket SKU                                  | Wet-market request                              | Common substitutes                          | Dietary flags |
| ---------------- | ---------------- | --------------------- | ------------------------------------------------ | ----------------------------------------------- | ------------------------------------------- | ------------- |
| **Chicken**      | Ayam             | 鸡                    | Whole kampong chicken 1.2–1.5 kg (S$10–14)        | "Ayam kampong 1.5 kg, jangan terlalu gemuk"      | Free-range supermarket chicken              | halal ⁴       |
| **Pork**         | Babi             | 猪                    | n/a — supermarkets do NOT sell pork               | "Babi 500g, lean, minta tolong potong dadu"      | Chicken thigh (1:1, different flavour)      | —             |

⁴ Whole chicken at the wet market: ask for *ayam kampung* (kampong) for the Hainanese chicken rice flavour. *Ayam biasa* (regular broiler) is cheaper but less flavourful.

### Pantry / starches

| English          | Malay / regional | 中文 (Chinese)        | Supermarket SKU                                  | Wet-market request                              | Common substitutes                          | Dietary flags |
| ---------------- | ---------------- | --------------------- | ------------------------------------------------ | ----------------------------------------------- | ------------------------------------------- | ------------- |
| **Coconut milk** | Santan           | 椰浆                  | Kara 400ml tetra (S$2.50) or KARA 1L carton     | "Santan segar 500ml" (fresh pressed; 2× price, 3× flavour) | Diluted coconut cream (1:1)                 | vegan, halal  |
| **Rice**         | Beras            | 米                    | Royal Umbrella Thai Hom Mali 5 kg (S$12)         | n/a — supermarkets only                          | Japanese short-grain (stickier, different)  | vegan, halal  |

## Pronunciation cheat sheet (wet-market survival)

- **Bawang merah** = *bah-wahng meh-rah* (red shallot)
- **Bawang putih** = *bah-wahng poo-teh* (garlic)
- **Halia** = *hah-lee-ah* (ginger)
- **Lengkuas** = *lehng-koo-ahs* (galangal)
- **Serai** = *seh-rai* (lemongrass)
- **Kunyit** = *koon-yit* (turmeric)
- **Buah keras** = *boo-ah keh-rahs* (candlenut)
- **Belacan** = *beh-lah-chan* (shrimp paste)
- **Kicap pekat** = *kee-chahp peh-kaht* (dark soy)
- **Kicap cair** = *kee-chahp cha-eer* (light soy)
- **Kicap ikan** = *kee-chahp ee-kahn* (fish sauce)
- **Sambal** = *sahm-bahl* (chilli paste)
- **Limau kasturi** = *lee-mow kahs-too-ree* (calamansi)
- **Kangkung** = *kahng-koo-ng* (water spinach)
- **Ayam** = *ah-yahm* (chicken)
- **Babi** = *bah-bee* (pork)
- **Santan** = *sahn-tahn* (coconut milk)
- **Beras** = *beh-rahs* (rice)

If the vendor speaks only Mandarin, fall back to the Chinese column. If the vendor speaks Malay, use the Malay column. Most wet-market vendors will switch to whatever language you start with — so start with "Halia 200g" in Malay and you will be fine.

## Substitutions & dietary flags — the rules

1. **If a recipe calls for belacan and the user is vegetarian/vegan**: substitute Thai *kapi* (1:1, but check the label) or a *vegan shrimp paste alternative* (e.g. the S$5 "Plant-Based Shrimp Paste" at NTUC Cold Storage) at 1:1. Do NOT suggest belacan.
2. **If a recipe calls for pork and the user is halal/no-pork**: substitute chicken thigh (1:1, same cook time) or beef cheek (1:1, +20 min cook time).
3. **If a recipe calls for dark soy and the user is gluten-free**: substitute *tamari* (Japanese, 1:1, but check the label for "no wheat").
4. **If a recipe calls for fish sauce and the user is vegan**: substitute *Thai vegan fish sauce* (e.g. the S$6 "Healthy Boy" brand) at 1:1, or use 1 tsp miso + 1 tsp water.
5. **If a recipe calls for Shaoxing wine and the user is halal**: substitute *Chinese rice wine* (Mirin is *not* halal — it contains alcohol in non-trivial amounts) or *Mirin-style halal seasoning* (S$4 at NTUC).

## What this dictionary does NOT cover

- **Snake fruit, durian, jackfruit, soursop, mangosteen** — these are *fruit*, not *cooking ingredients*. Use the **sg-fruit-price-tracker-skill** for those.
- **Whole live seafood (fish, prawns, crabs, lobsters)** — pricing varies daily; this dictionary lists *cooking ingredients*, not *raw proteins for steaming*. For live seafood pricing, ask the wet-market vendor directly.
- **Halal/non-halal cuts of beef and lamb** — these vary by vendor. Ask the wet-market vendor for *daging halal* (halal beef) or *daging biasa* (regular beef).
