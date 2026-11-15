# Audio script: clips to record

Written for the person recording the voice (Darija and French).

The app builds each spoken sentence from short clips. Example: "November to December: sow wheat" = `month_11` + `to` + `month_12` + `act_sow` + `crop_wheat`. When every clip of a sentence exists, the app plays them; if one is missing, the phone's voice reads the whole sentence instead.

## How to record

- One file per line below, **MP3**, mono, named exactly like the id: `frontend/public/audio/ar/<id>.mp3` (Darija) and `frontend/public/audio/fr/<id>.mp3` (French). `ar` is the folder for Darija.
- Calm, slow voice, as if speaking to a farmer. Leave about 0.2 s of silence at the start and the end of each clip.
- Read the Darija column as written. It is also in `docs/darija-review.md`: if you correct a word there, record the corrected version.
- Compare-card sentences mix numbers and months, so they are read by the phone's voice only. Nothing to record for them.

## Clips (53 per language)

| File id | Darija | French | Note |
|---|---|---|---|
| `month_1` | يناير | janvier |  |
| `month_2` | فبراير | février |  |
| `month_3` | مارس | mars |  |
| `month_4` | أبريل | avril |  |
| `month_5` | ماي | mai |  |
| `month_6` | يونيو | juin |  |
| `month_7` | يوليوز | juillet |  |
| `month_8` | غشت | août |  |
| `month_9` | شتنبر | septembre |  |
| `month_10` | أكتوبر | octobre |  |
| `month_11` | نونبر | novembre |  |
| `month_12` | دجنبر | décembre |  |
| `to` | حتى | jusqu’à | between two months: "November to December" |
| `plan_intro` | الخطة ديالك: | Votre plan : |  |
| `then` | من بعد | puis |  |
| `act_sow` | زرع | Semer | followed by a crop clip |
| `act_harvest` | حصد | Récolter | followed by a crop clip |
| `act_watch_water` | رد البال للما ديال | Surveiller l’eau pour | followed by a crop clip |
| `act_cover_bare` | ما تخلّيش التربة خاوية إلا قدرتي | Ne laissez pas le sol nu si possible |  |
| `act_cover_fallow` | الأرض كترتاح: ما تخلّيهاش خاوية إلا قدرتي | Champ au repos : ne le laissez pas nu si possible |  |
| `act_avoid` | رد البال: | Attention : | followed by a crop clip |
| `act_avoid_end` | جا مور زرع من نفس العائلة | vient après une culture de la même famille |  |
| `crop_wheat` | القمح | le blé | French with its article, as it is said after a verb |
| `crop_barley` | الشعير | l’orge | French with its article, as it is said after a verb |
| `crop_chickpea` | الحمّص | les pois chiches | French with its article, as it is said after a verb |
| `crop_lentil` | العدس | les lentilles | French with its article, as it is said after a verb |
| `crop_faba_bean` | الفول | les fèves | French with its article, as it is said after a verb |
| `crop_alfalfa` | الفصّة | la luzerne | French with its article, as it is said after a verb |
| `crop_vetch_oat_cover` | البيقة والخرطال (تغطية) | la vesce et l’avoine | French with its article, as it is said after a verb |
| `crop_sunflower` | النوّار ديال الشمس | le tournesol | French with its article, as it is said after a verb |
| `crop_potato` | البطاطا | la pomme de terre | French with its article, as it is said after a verb |
| `crop_olive_intercrop` | زريعة بين الزيتون | la culture entre les oliviers | French with its article, as it is said after a verb |
| `crop_fallow` | البور | la jachère | French with its article, as it is said after a verb |
| `why_step_sow_why` | هادا هو الشهر اللي كيتزرع فيه هاد الزرع عادة؛ تأكد من النهار مع ناس المنطقة. | Mois de semis habituel pour cette culture ; confirmez la date localement. |  |
| `why_step_harvest_why` | هادا هو الشهر اللي كيتحصد فيه هاد الزرع عادة. | Mois de récolte habituel pour cette culture. |  |
| `why_step_perennial_why` | هاد الزرع كيبقى فالفدّان العام كامل: كيتزرع مرة وحدة، ماشي كل موسم. | Cette culture reste dans le champ toute l’année : on l’installe une fois, on ne la sème pas à chaque saison. |  |
| `why_step_water_why` | فهاد الشهور الشتا غالبا قلّ من الما اللي خاص هاد الزرع. | La pluie est souvent inférieure au besoin de cette culture pendant ces mois. |  |
| `why_step_bare_why` | التربة الخاوية كيديها الما والريح؛ زرع التغطية كيحميها. | Un sol nu est exposé à l’érosion ; une culture de couverture le protège. |  |
| `why_step_fallow_why` | الأرض اللي كترتاح كتبقى خاوية؛ زرع التغطية يقدر يحميها. | Un champ au repos est un sol nu ; une culture de couverture le protégerait. |  |
| `why_step_avoid_family_why` | نفس العائلة ديال الزرع كتخلّي الأمراض والحشرات ديالها فالتربة. | La même famille de cultures garde ses ravageurs et maladies dans le sol. |  |
| `v_water` | الما | Eau |  |
| `v_soil` | التربة | Sol |  |
| `v_pests` | الحشرات والأمراض | Ravageurs |  |
| `v_water_good` | الشتا كافي | Assez de pluie |  |
| `v_water_some` | شي شهور ناشفين | Quelques mois secs |  |
| `v_water_dry` | ناشف بزاف المرات | Souvent trop sec |  |
| `v_soil_up` | التربة كتحسن | Le sol s’améliore |  |
| `v_soil_flat` | التربة بحالها | Le sol reste pareil |  |
| `v_soil_down` | التربة كتعيا | Le sol s’épuise |  |
| `v_pests_break` | الدورة ديال الحشرات مقطوعة | Cycle des ravageurs cassé |  |
| `v_pests_repeat` | نفس العائلة كتعاود | Même famille répétée |  |
| `v_pests_unknown` | ما تقيّمش | Non évalué |  |
| `talk_expert` | هضر مع مستشار فلاحي فالمنطقة ديالك قبل ما تقرّر. هاد النتائج كتعاونك تفكّر، ولكن ماشي هي اللي كتقرّر بلاصتك. | Parlez à un conseiller agricole de votre région avant de décider. Ces résultats aident à réfléchir, ils ne décident pas à votre place. | always played at the end of "Listen to the plan" |
