"""User-facing strings for the UI and the result card (Turkish default, English).

Item content (stems, options, explanations) is English by design and is not
translated here.
"""

from __future__ import annotations

DEFAULT_LANGUAGE = "tr"
LANGUAGES = {"tr": "Türkçe", "en": "English"}

STRINGS: dict[str, dict[str, str]] = {
    "tr": {
        "app_title": "İngilizce Seviye Testi",
        "app_subtitle": "CEFR uyumlu tahmin · yaklaşık 15 dakika · {length} soru",
        "intro": (
            "Bu test dilbilgisi, kelime bilgisi ve okuma becerinizi ölçer ve CEFR seviyenizi (A1–C2) "
            "tahmin eder. Sorular verdiğiniz yanıtlara göre zorlaşır veya kolaylaşır. Süre sınırı yoktur; "
            "bilmediğiniz soruda en makul seçeneği işaretleyin."
        ),
        "start_disclaimer": (
            "Sonuç resmi bir sertifika değil, CEFR ile uyumlu bir tahmindir. Dinleme, konuşma ve yazma ölçülmez."
        ),
        "email_label": "E-posta adresiniz",
        "email_help": (
            "Yalnızca testi tekrar çözdüğünüzde farklı sorular gösterebilmek için kullanılır. "
            "E-postanız saklanmaz; yalnızca anahtarlı bir özeti (hash) kaydedilir."
        ),
        "invalid_email": "Lütfen geçerli bir e-posta adresi girin.",
        "advanced": "Gelişmiş",
        "mode_label": "Test biçimi",
        "mode_adaptive": "Uyarlamalı (önerilen)",
        "mode_fixed": "Sabit form (karşılaştırma ve hata ayıklama için)",
        "start_button": "Teste başla",
        "language_label": "Dil / Language",
        "attempt_info": "Bu sizin {attempt}. denemeniz. Önceki denemelerde gördüğünüz sorular mümkün olduğunca tekrar gösterilmez.",
        "progress": "Soru {n} / {total}",
        "elapsed": "Geçen süre: {minutes:02d}:{seconds:02d} · önerilen süre yaklaşık 15 dakika (süre sınırı yok)",
        "passage_label": "Metni okuyun",
        "choose_option": "Seçenekler",
        "next_button": "İleri",
        "quit_button": "Testi bitir",
        "quit_help": "Yanıtladığınız sorular kaydedilir. En az {min} soru yanıtladıysanız kısmi bir sonuç gösterilir.",
        "no_result": "{n} soru yanıtlandı. Sonuç gösterebilmek için en az {min} yanıt gerekir.",
        "retake_button": "Testi yeniden çöz (farklı sorular)",
        "download_button": "Sonuç kartını indir (.md)",
        "repeat_notice": (
            "Not: Soru havuzu yeterli olmadığı için bu denemede bazı sorular önceki denemelerinizden "
            "tekrar kullanıldı. Bu, sonucu bir miktar iyimser yapabilir."
        ),
        # Result card
        "card_title": "Sonuç kartı",
        "headline": "{level} · {group}",
        "scaled_score": "Ölçekli puan: {score} / 100",
        "can_do_title": "Bu seviyede genellikle şunları yapabilirsiniz",
        "confidence_title": "Sonucun güvenilirliği",
        "confidence_clear": "Sonucunuz büyük olasılıkla {level} seviyesidir.",
        "confidence_borderline": (
            "Sonucunuz {low}/{high} sınırına yakın: iki seviye de makul. Başlık en olası seviyeyi gösterir."
        ),
        "probabilities": "Seviye olasılıkları: {items}",
        "se_note": "Yetenek tahmini θ = {theta:+.2f}, ölçüm hatası (SE) = {se:.2f}.",
        "incomplete": "Test tamamlanmadı ({n} / {total} soru); sonuç daha belirsizdir.",
        "subskills_title": "Alt beceriler",
        "subskill_row": "{name}: {level} bandı · %{pct:.0f} doğru ({n} soru)",
        "subskill_suppressed": "{name}: yeterli soru yok ({n} soru; en az {min} gerekir)",
        "subskill_note": (
            "Alt beceri bantları daha az soruya dayanır ve gösterge niteliğindedir. Sorular seviyenize göre "
            "zorlaştığı için doğru yüzdesi kişiler arasında karşılaştırılamaz."
        ),
        "strengths_title": "Güçlü yönler",
        "focus_title": "Odaklanılacak alanlar",
        "tag_row": "{tag} ({n} soru)",
        "tags_none": "Bu ayrım için yeterli veri yok.",
        "tags_note": "Seviyenize göre beklenenden daha iyi veya daha zayıf olduğunuz beceriler; parantez içinde dayanılan soru sayısı.",
        "plan_title": "Bir sonraki seviye için eylem planı",
        "review_title": "Yanlış yanıtladığınız sorular",
        "review_note": "Açıklamalar İngilizcedir.",
        "review_none": "Yanlış yanıtınız yok.",
        "review_your_answer": "Yanıtınız",
        "review_correct": "Doğru yanıt",
        "disclaimer_title": "Önemli not",
        "disclaimer": (
            "Bu sonuç CEFR ile uyumlu bir tahmindir; resmi bir sertifika değildir. Soru parametreleri uzman "
            "tahminlerine dayanır ve gerçek yanıt verileriyle kalibre edilene kadar geçicidir. Test yalnızca "
            "dilbilgisi, kelime ve okuma becerilerini kapsar; dinleme, konuşma ve yazma ölçülmez. Daha güvenilir "
            "bir tahmin için birkaç hafta sonra testi yeniden çözebilirsiniz."
        ),
        # Domains
        "domain_grammar": "Dilbilgisi",
        "domain_vocabulary": "Kelime bilgisi",
        "domain_reading": "Okuma",
        # Plan, general steps
        "plan_read_basic": "Her gün 15 dakika, seviyenizin biraz üstündeki kısa ve basit metinler (kolaylaştırılmış hikâyeler, kısa haberler) okuyun.",
        "plan_read_independent": "Haftada 2–3 makale okuyun ve her birinden 5 kullanışlı ifadeyi örnek cümleleriyle not alın.",
        "plan_read_proficient": "Her hafta zorlu metinler (görüş yazıları, raporlar) okuyun ve her birini 3–4 cümleyle özetleyin.",
        "plan_vocab": "Haftada 10 yeni kelimeyi örnek cümle içinde öğrenin; 1, 3 ve 7 gün sonra tekrar edin. (haftada yaklaşık 30 dk)",
        "plan_time": (
            "Yaygın kullanılan kaba bir ölçüye göre bir CEFR seviyesi ilerlemek yaklaşık 200 saatlik rehberli "
            "çalışma gerektirir; düzenli çalışmayla birkaç ay planlayın. 8–12 hafta sonra testi yeniden çözerek "
            "ilerlemenizi kontrol edin."
        ),
        "plan_time_top": (
            "C2'de amaç bir seviye atlamak değil, İngilizcenizi korumak ve genişletmektir. Farklı türlerde "
            "(akademik, edebi, teknik) düzenli okuma yapın ve birkaç ayda bir kendinizi yeniden ölçün."
        ),
    },
    "en": {
        "app_title": "English Placement Test",
        "app_subtitle": "CEFR-aligned estimate · about 15 minutes · {length} questions",
        "intro": (
            "This test measures your grammar, vocabulary and reading and estimates your CEFR level (A1–C2). "
            "Questions get harder or easier depending on your answers. There is no time limit; if you are not "
            "sure, choose the most likely option."
        ),
        "start_disclaimer": (
            "The result is a CEFR-aligned estimate, not an official certificate. Listening, speaking and writing are not measured."
        ),
        "email_label": "Your email address",
        "email_help": (
            "Used only to show you different questions if you take the test again. Your email is not stored; "
            "only a keyed hash of it is saved."
        ),
        "invalid_email": "Please enter a valid email address.",
        "advanced": "Advanced",
        "mode_label": "Test format",
        "mode_adaptive": "Adaptive (recommended)",
        "mode_fixed": "Fixed form (for comparison and debugging)",
        "start_button": "Start the test",
        "language_label": "Dil / Language",
        "attempt_info": "This is your attempt number {attempt}. Questions from earlier attempts are avoided where possible.",
        "progress": "Question {n} of {total}",
        "elapsed": "Time so far: {minutes:02d}:{seconds:02d} · suggested time about 15 minutes (no time limit)",
        "passage_label": "Read the text",
        "choose_option": "Options",
        "next_button": "Next",
        "quit_button": "Finish the test",
        "quit_help": "Your answers so far are saved. If you have answered at least {min} questions, a partial result is shown.",
        "no_result": "{n} questions answered. At least {min} answers are needed to show a result.",
        "retake_button": "Take the test again (different questions)",
        "download_button": "Download result card (.md)",
        "repeat_notice": (
            "Note: the question bank was not large enough, so some questions from your earlier attempts were "
            "reused. This may make the result slightly optimistic."
        ),
        "card_title": "Result card",
        "headline": "{level} · {group}",
        "scaled_score": "Scaled score: {score} / 100",
        "can_do_title": "At this level you can typically",
        "confidence_title": "How sure is this result?",
        "confidence_clear": "Your result is most likely {level}.",
        "confidence_borderline": (
            "Your result is close to the {low}/{high} boundary: both levels are plausible. The headline shows the more likely one."
        ),
        "probabilities": "Level probabilities: {items}",
        "se_note": "Ability estimate θ = {theta:+.2f}, standard error (SE) = {se:.2f}.",
        "incomplete": "The test was not completed ({n} of {total} questions), so the result is less certain.",
        "subskills_title": "Sub-skills",
        "subskill_row": "{name}: {level} band · {pct:.0f}% correct ({n} questions)",
        "subskill_suppressed": "{name}: not enough items ({n} questions; at least {min} needed)",
        "subskill_note": (
            "Sub-skill bands rest on fewer questions and are indicative only. Because questions adapt to your level, "
            "% correct cannot be compared between people."
        ),
        "strengths_title": "Strengths",
        "focus_title": "Focus areas",
        "tag_row": "{tag} ({n} questions)",
        "tags_none": "Not enough data for this breakdown.",
        "tags_note": "Skills where you did better or worse than expected for your level; the number of questions behind each is in brackets.",
        "plan_title": "Action plan for the next level",
        "review_title": "Questions you missed",
        "review_note": "Explanations are in English.",
        "review_none": "You did not miss any questions.",
        "review_your_answer": "Your answer",
        "review_correct": "Correct answer",
        "disclaimer_title": "Please note",
        "disclaimer": (
            "This result is a CEFR-aligned estimate, not an official certificate. The question parameters are expert "
            "estimates and remain provisional until they are calibrated with real response data. The test covers "
            "grammar, vocabulary and reading only; listening, speaking and writing are not measured. For a more "
            "reliable estimate, take the test again in a few weeks."
        ),
        "domain_grammar": "Grammar",
        "domain_vocabulary": "Vocabulary",
        "domain_reading": "Reading",
        "plan_read_basic": "Read short, simple texts (graded readers, short news items) slightly above your level for 15 minutes a day.",
        "plan_read_independent": "Read 2–3 articles a week and note 5 useful phrases from each, with an example sentence.",
        "plan_read_proficient": "Read demanding texts (opinion pieces, reports) every week and summarise each in 3–4 sentences.",
        "plan_vocab": "Learn 10 new words a week in example sentences and review them after 1, 3 and 7 days. (about 30 min/week)",
        "plan_time": (
            "A widely used rough guide is about 200 hours of guided study to move up one CEFR level, so plan for "
            "several months of regular practice. Retake this test in 8–12 weeks to check your progress."
        ),
        "plan_time_top": (
            "At C2 the goal is to maintain and broaden your English rather than move up a level. Read widely "
            "(academic, literary, technical) and re-check yourself every few months."
        ),
    },
}

LEVEL_GROUPS: dict[str, dict[str, str]] = {
    "tr": {
        "A1": "Temel Kullanıcı — Başlangıç",
        "A2": "Temel Kullanıcı — Temel",
        "B1": "Bağımsız Kullanıcı — Orta",
        "B2": "Bağımsız Kullanıcı — Orta Üstü",
        "C1": "Yetkin Kullanıcı — İleri",
        "C2": "Yetkin Kullanıcı — Ustalık",
    },
    "en": {
        "A1": "Basic User — Breakthrough",
        "A2": "Basic User — Waystage",
        "B1": "Independent User — Threshold",
        "B2": "Independent User — Vantage",
        "C1": "Proficient User — Effective Operational Proficiency",
        "C2": "Proficient User — Mastery",
    },
}

# Original paraphrases of typical abilities at each level (not CEFR quotations).
CAN_DO: dict[str, dict[str, tuple[str, ...]]] = {
    "tr": {
        "A1": (
            "Kendiniz, aileniz ve günlük düzeniniz hakkında kısa, tanıdık ifadeleri anlayıp kullanmak.",
            "Karşınızdaki yavaş konuşup yardımcı olursa basit kişisel soruları sorup yanıtlamak.",
        ),
        "A2": (
            "Alışveriş, iş ve seyahat planları gibi gündelik konulardaki kısa, basit metinleri anlamak.",
            "Buluşma ayarlamak veya yemek sipariş etmek gibi rutin konuşmaları basit cümlelerle yürütmek.",
            "Geçmişinizi ve yakın zamandaki olayları temel geçmiş zaman yapılarıyla anlatmak.",
        ),
        "B1": (
            "İş, okul ve boş zaman konularındaki açık metinlerin ana noktalarını izlemek.",
            "Seyahatte karşılaşılan çoğu durumla başa çıkmak ve tanıdık konularda bağlantılı basit metinler yazmak.",
            "Görüşleriniz ve planlarınız için kısa gerekçeler sunmak.",
        ),
        "B2": (
            "Kendi alanınızdaki tartışmalar dahil, oldukça karmaşık metinlerin ana fikirlerini anlamak.",
            "Akıcı konuşanlarla görece rahat biçimde sohbete katılmak.",
            "Açık ve ayrıntılı metinler yazmak, bir görüşün lehinde veya aleyhinde gerekçe sunmak.",
        ),
        "C1": (
            "Uzun ve zorlu metinleri anlamak; açıkça söylenenin yanında ima edileni de fark etmek.",
            "Kendinizi akıcı biçimde ifade etmek ve dilinizi sosyal, akademik ve iş ortamlarına uyarlamak.",
            "Karmaşık konularda iyi düzenlenmiş, ayrıntılı metinler üretmek.",
        ),
        "C2": (
            "Soyut ve ince anlam farkları içeren yazılar dahil, okuduğunuz hemen her şeyi rahatça anlamak.",
            "Farklı kaynaklardan gelen bilgileri tutarlı bir argümanda özetlemek.",
            "Karmaşık durumlarda bile ince anlam ayrımlarını kesin biçimde ifade etmek.",
        ),
    },
    "en": {
        "A1": (
            "Understand and use short, familiar phrases about yourself, your family and your daily routine.",
            "Ask and answer simple personal questions if the other person speaks slowly and helps you.",
        ),
        "A2": (
            "Understand short, simple texts on everyday topics such as shopping, work and travel plans.",
            "Handle routine exchanges, such as making arrangements or ordering food, in simple sentences.",
            "Describe your background and recent events using basic past forms.",
        ),
        "B1": (
            "Follow the main points of clear texts about work, study and leisure.",
            "Deal with most situations while travelling and write simple connected text on familiar topics.",
            "Give brief reasons for your opinions and plans.",
        ),
        "B2": (
            "Understand the main ideas of fairly complex texts, including discussions in your own field.",
            "Take part in conversations with fluent speakers fairly comfortably.",
            "Write clear, detailed text and argue for or against a point of view.",
        ),
        "C1": (
            "Understand long, demanding texts and notice what is implied as well as what is stated.",
            "Express yourself fluently and adapt your language to social, academic and work settings.",
            "Produce well-organised, detailed text on complex subjects.",
        ),
        "C2": (
            "Understand almost anything you read with ease, including abstract and nuanced writing.",
            "Summarise information from different sources into one coherent argument.",
            "Express fine shades of meaning precisely, even in complex situations.",
        ),
    },
}

TAG_NAMES: dict[str, dict[str, str]] = {
    "tr": {
        "Tenses & aspect": "Zamanlar ve görünüş",
        "Verb patterns & agreement": "Fiil kalıpları ve uyum",
        "Articles & determiners": "Tanımlıklar ve belirleyiciler",
        "Prepositions": "Edatlar (prepositions)",
        "Comparatives & quantifiers": "Karşılaştırma ve miktar sözcükleri",
        "Modal verbs": "Kip fiilleri (modals)",
        "Conditionals & hypotheticals": "Koşul ve varsayım cümleleri",
        "Passive & causative": "Edilgen ve ettirgen yapılar",
        "Clause structure": "Yan cümle yapısı",
        "Inversion & emphasis": "Devrik yapı ve vurgu",
        "Word choice": "Sözcük seçimi",
        "Collocations": "Eşdizimler (collocations)",
        "Phrasal verbs": "Öbek fiiller (phrasal verbs)",
        "Idioms & fixed expressions": "Deyimler ve kalıp ifadeler",
        "Register & pragmatics": "Üslup ve kullanım bağlamı",
        "Word formation": "Sözcük türetme",
        "Main idea": "Ana fikir",
        "Detail": "Ayrıntı",
        "Inference": "Çıkarım",
        "Vocabulary in context": "Bağlamda sözcük anlamı",
    },
    "en": {},
}

# One concrete, level-independent practice step per skill tag.
TAG_ADVICE: dict[str, dict[str, str]] = {
    "tr": {
        "Tenses & aspect": "Haftada bir, geçmiş, present perfect ve gelecek zamanları karıştıran 8–10 cümlelik kısa bir günlük yazın; her fiili bir dilbilgisi kaynağından kontrol edin. (haftada ~30 dk)",
        "Verb patterns & agreement": "-ing veya to + fiil alan fiillerin listesini tutun (enjoy doing, decide to do); her hafta 5 tane ekleyip her biriyle bir cümle yazın. (haftada ~20 dk)",
        "Articles & determiners": "Kısa bir metindeki a/an/the'leri silip yeniden doldurun ve asılla karşılaştırın; haftada iki kez. (haftada ~20 dk)",
        "Prepositions": "Edatları kalıp hâlinde öğrenin (on Monday, at 9, interested in); okuduklarınızdan haftada 10 kalıp toplayın. (haftada ~20 dk)",
        "Comparatives & quantifiers": "İyi bildiğiniz iki şeyi (şehirler, telefonlar, işler) karşılaştırma yapıları ve much/a few/fewer ile 6 cümlede karşılaştırın. (haftada 2 × 15 dk)",
        "Modal verbs": "Gerçek durumlar hakkında kurallar, olasılıklar ve tahminler için haftada 5 cümle yazın (must, might, should have, can't have). (haftada ~20 dk)",
        "Conditionals & hypotheticals": "Her hafta kendi hayatınızla ilgili 3 gerçek ve 3 hayalî 'if' cümlesi yazın; en az biri geçmişle ilgili olsun. (haftada ~20 dk)",
        "Passive & causative": "5 haber başlığını tam edilgen cümlelere çevirin ve yaptırdığınız 3 işi anlatın (I had my hair cut). (haftada ~20 dk)",
        "Clause structure": "Kısa cümle çiftlerini who/which/that, ortaç yapıları ve bağlaçlarla birleştirin; haftada 8 örnek. (haftada ~25 dk)",
        "Inversion & emphasis": "Resmî metinlerden devrik yapı ve vurgu cümlesi örnekleri toplayın; her hafta 5 düz cümleyi vurgulu hâle getirin. (haftada ~20 dk)",
        "Word choice": "Bir sözcüğe baktığınızda karıştırılan bir sözcüğü ve farkını da not edin (close/closed, louder/higher); haftada 5 çift. (haftada ~20 dk)",
        "Collocations": "İsimlere göre düzenlenmiş bir eşdizim defteri tutun (take measures, make a decision); okuduklarınızdan haftada 10 ekleyin. (haftada ~25 dk)",
        "Phrasal verbs": "Haftada 10 öbek fiili bağlam içinde çalışın; her biri için 3 cümle yazın ve hafta sonunda kendinizi sınayın. (haftada ~40 dk)",
        "Idioms & fixed expressions": "Haftada 5 yaygın deyimi gerçek bir örnek cümleyle öğrenin; bağlamsız listelerden kaçının. (haftada ~20 dk)",
        "Register & pragmatics": "Haftada 3 kısa mesajı iki üslupta yeniden yazın (bir arkadaşa / bir şirkete) ve farkları not edin. (haftada ~25 dk)",
        "Word formation": "Her yeni sözcüğün ailesini not edin (succeed, success, successful, successfully) ve iki biçimiyle bir cümle yazın. (haftada ~20 dk)",
        "Main idea": "Kısa bir yazıyı okuduktan sonra, yeniden okumadan tek cümlelik bir özet yazın; özetin metnin tamamını kapsayıp kapsamadığını kontrol edin. (haftada 3 metin, ~30 dk)",
        "Detail": "Kısa metinleri aklınızda bir soruyla okuyun ve yanıtı veren tam sözcüklerin altını çizin. (haftada 3 metin, ~30 dk)",
        "Inference": "Görüş yazılarında yazarın açıkça söylemeden ima ettiklerini ve bunu gösteren sözcükleri not edin. (haftada 2 metin, ~30 dk)",
        "Vocabulary in context": "Bilmediğiniz sözcüğün anlamını sözlüğe bakmadan önce bağlamdan tahmin edin; sonra tahmininizi kontrol edip nedenini not edin. (haftada 3 × 15 dk)",
    },
    "en": {
        "Tenses & aspect": "Once a week, write a short diary entry (8–10 sentences) mixing past simple, present perfect and future forms, then check each verb in a grammar reference. (about 30 min/week)",
        "Verb patterns & agreement": "Keep a list of verbs followed by -ing or to + verb (enjoy doing, decide to do); add 5 a week and write one sentence for each. (about 20 min/week)",
        "Articles & determiners": "Delete the articles from a short text, fill them in again and compare with the original; twice a week. (about 20 min/week)",
        "Prepositions": "Learn prepositions in chunks (on Monday, at 9, interested in); collect 10 chunks a week from your reading. (about 20 min/week)",
        "Comparatives & quantifiers": "Compare two things you know well (cities, phones, jobs) in 6 sentences using comparatives and quantifiers such as much, a few and fewer. (2 × 15 min/week)",
        "Modal verbs": "Write 5 sentences a week about rules, possibilities and guesses in real situations (must, might, should have, can't have). (about 20 min/week)",
        "Conditionals & hypotheticals": "Each week, write 3 real and 3 imaginary 'if' sentences about your own life, at least one about the past. (about 20 min/week)",
        "Passive & causative": "Rewrite 5 news headlines as full passive sentences and describe 3 services you had done (I had my hair cut). (about 20 min/week)",
        "Clause structure": "Join pairs of short sentences using who/which/that, participle clauses and linking words; aim for 8 a week. (about 25 min/week)",
        "Inversion & emphasis": "Collect examples of inversion and emphatic sentences from formal texts; rewrite 5 plain sentences for emphasis each week. (about 20 min/week)",
        "Word choice": "When you look up a word, also note one word it is often confused with and the difference (close/closed, louder/higher); 5 pairs a week. (about 20 min/week)",
        "Collocations": "Keep a collocation notebook organised by noun (take measures, make a decision); add 10 a week from texts you read. (about 25 min/week)",
        "Phrasal verbs": "Practise 10 phrasal verbs a week in context; write 3 sentences for each and test yourself at the end of the week. (about 40 min/week)",
        "Idioms & fixed expressions": "Learn 5 common idioms a week, each with a real example sentence; avoid lists without context. (about 20 min/week)",
        "Register & pragmatics": "Rewrite 3 short messages a week in two styles (to a friend / to a company) and note what changes. (about 25 min/week)",
        "Word formation": "For each new word, note its family (succeed, success, successful, successfully) and write one sentence using two of the forms. (about 20 min/week)",
        "Main idea": "After reading a short article, write a one-sentence summary before rereading it, then check that it covers the whole text. (3 texts/week, about 30 min)",
        "Detail": "Read short texts with a question in mind and underline the exact words that answer it. (3 texts/week, about 30 min)",
        "Inference": "When reading opinion pieces, note what the writer implies without saying it, and the words that show it. (2 texts/week, about 30 min)",
        "Vocabulary in context": "Guess unknown words from context before using a dictionary, then check your guess and note why it was right or wrong. (3 × 15 min/week)",
    },
}


# --- Web interface (landing page, test screen, result screen) -----------------

_WEB_STRINGS: dict[str, dict[str, str]] = {
    "tr": {
        "brand": "Seviye",
        "brand_tag": "CEFR uyumlu İngilizce seviye testi",
        "hero_badge": "Ücretsiz · Kayıt gerekmez · Reklamsız",
        "hero_title": "İngilizce seviyenizi <em>15 dakikada</em> öğrenin",
        "hero_sub": (
            "Sorular yanıtlarınıza göre uyarlanır. Sonunda yalnızca bir harf değil; seviyenizi, ne kadar emin "
            "olduğumuzu, güçlü ve zayıf becerilerinizi ve size özel bir çalışma planını görürsünüz."
        ),
        "cta_title": "Teste başlayın",
        "cta_note": "E-postanız saklanmaz; yalnızca şifreli özeti tutulur.",
        "stat_questions": "{n} soru",
        "stat_questions_label": "uyarlamalı",
        "stat_minutes": "~15 dk",
        "stat_minutes_label": "süre sınırı yok",
        "stat_levels": "A1–C2",
        "stat_levels_label": "6 CEFR seviyesi",
        "stat_skills": "3 beceri",
        "stat_skills_label": "dilbilgisi · kelime · okuma",
        "how_title": "Nasıl çalışır?",
        "how_sub": "Herkese aynı soruları sormak yerine, test sizi tanıdıkça kendini ayarlar.",
        "step1_title": "Isınma",
        "step1_text": "İlk 10 soru farklı seviyelerden gelir ve kabaca nerede olduğunuzu belirler.",
        "step2_title": "Uyarlama",
        "step2_text": "Sonraki 10 soru tam sizin seviyenize göre seçilir; çok kolay ya da imkânsız sorularla zaman kaybetmezsiniz.",
        "step3_title": "İnce ayar",
        "step3_text": "Son 8 soru, iki seviye arasındaki sınırı netleştirmek için seçilir.",
        "step4_title": "Sonuç ve plan",
        "step4_text": "Seviyeniz, olasılıklar, alt beceriler ve haftalık süresi belli somut adımlar.",
        "features_title": "Neden bu test?",
        "feat1_title": "Dürüst sonuç",
        "feat1_text": "Tek bir etiket yerine seviye olasılıklarını gösterir ve iki seviye arasındaysanız bunu açıkça söyler.",
        "feat2_title": "Tanı odaklı sorular",
        "feat2_text": "Her yanlış seçenek belirli bir hatayı hedefler; hangi konularda takıldığınızı görürsünüz.",
        "feat3_title": "Kişisel çalışma planı",
        "feat3_text": "Plan, en zayıf çıktığınız becerilere bağlıdır ve her adımın haftalık süresi yazılıdır.",
        "feat4_title": "Tekrar çözülebilir",
        "feat4_text": "Testi yeniden çözdüğünüzde önceki sorular mümkün olduğunca karşınıza çıkmaz.",
        "feat5_title": "Kaldığınız yerden",
        "feat5_text": "Sayfayı kapatırsanız aynı e-postayla döndüğünüzde test kaldığı yerden devam eder.",
        "feat6_title": "Gizlilik",
        "feat6_text": "Hesap yok, reklam yok, dış servis yok. E-postanız saklanmaz; test tamamen yerelde çalışır.",
        "cefr_title": "CEFR seviyeleri",
        "cefr_sub": "Avrupa Ortak Dil Çerçevesi, dil yeterliliğini altı seviyede tanımlar.",
        "faq_title": "Sık sorulan sorular",
        "footer": "CEFR uyumlu bir tahmindir; resmi bir sınav veya sertifika değildir.",
        "resume_found": "Yarım kalan bir testiniz var: {n} / {total} soru yanıtlanmış.",
        "resume_button": "Kaldığım yerden devam et",
        "resume_other_browser": (
            "Bu e-postayla başka bir tarayıcıda başlatılmış yarım bir test var. Güvenlik için o test yalnızca "
            "başlatıldığı tarayıcıdan sürdürülebilir; buradan yeni bir test başlatabilirsin."
        ),
        "fresh_button": "Yeni test başlat",
        "resumed_toast": "Testiniz kaldığı yerden geri yüklendi.",
        "resume_failed": "Yarım kalan test geri yüklenemedi (soru havuzu değişmiş); yeni bir test başlatıldı.",
        "unsure_label": "Emin değilim",
        "back_button": "Geri",
        "review_button": "Gözden geçir",
        "finish_stage_button": "Bölümü bitir",
        "finish_test_button": "Testi bitir",
        "confirm_stage": "Bu bölümü bitiriyorsun; {a}–{b}. sorulara artık dönemeyeceksin.",
        "confirm_test": "Testi bitiriyorsun; cevapların artık değiştirilemeyecek.",
        "nav_label": "Sorular",
        "nav_answered": "Soru {n}: cevaplandı, değiştirilebilir",
        "nav_current": "Soru {n}: şu an ekranda",
        "nav_next": "Soru {n}: sıradaki soru",
        "nav_locked": "Soru {n}: kilitli, bölümü bitti",
        "nav_upcoming": "Soru {n}: henüz gelmedi",
        "unsure_note": "«Emin değilim» yanlış sayılır; tahmin etmek şans eseri doğru çıkabilir.",
        "type_cloze": "Boşluk doldurma",
        "type_error_id": "Hatayı bulun",
        "type_reading": "Okuma",
        "type_lexical_pragmatic": "Kelime ve kullanım",
        "stage_1": "Isınma",
        "stage_2": "Uyarlama",
        "stage_3": "İnce ayar",
        "stage_toast_2": "Isınma bitti; {a}–{b}. soruların cevapları kilitlendi. Sorular artık seviyenize göre seçiliyor.",
        "stage_toast_3": "Uyarlama bitti; {a}–{b}. soruların cevapları kilitlendi. Son bölüm: iki seviye arasındaki sınırı netleştiriyoruz.",
        "timer_label": "Süre",
        "no_back_note": "Bu bölümdeki sorulara dönebilirsin; bölüm bitince cevaplar kilitlenir.",
        "result_eyebrow": "Tahmini CEFR seviyeniz",
        "result_correct": "{c} / {n} doğru",
        "result_time": "{minutes} dk {seconds} sn",
        "scale_title": "CEFR ölçeğindeki yeriniz",
        "prob_title": "Seviye olasılıkları",
        "copy_title": "Sonucu paylaşın",
        "copy_text": "İngilizce seviye testi sonucum: {level} · {group} · ölçekli puan {score}/100 (CEFR uyumlu tahmin).",
        "subskill_band": "{level}",
        "subskill_hidden": "Yetersiz veri",
        "subskill_items": "{n} soru · %{pct:.0f} doğru",
        "you_are_here": "Siz",
    },
    "en": {
        "brand": "Seviye",
        "brand_tag": "CEFR-aligned English level test",
        "hero_badge": "Free · No sign-up · No ads",
        "hero_title": "Find your English level <em>in 15 minutes</em>",
        "hero_sub": (
            "Questions adapt to your answers. At the end you get more than a letter: your level, how sure we are, "
            "your strong and weak skills, and a study plan made for you."
        ),
        "cta_title": "Start the test",
        "cta_note": "Your email is not stored; only a keyed hash is kept.",
        "stat_questions": "{n} questions",
        "stat_questions_label": "adaptive",
        "stat_minutes": "~15 min",
        "stat_minutes_label": "no time limit",
        "stat_levels": "A1–C2",
        "stat_levels_label": "6 CEFR levels",
        "stat_skills": "3 skills",
        "stat_skills_label": "grammar · vocabulary · reading",
        "how_title": "How it works",
        "how_sub": "Instead of giving everyone the same questions, the test adjusts as it gets to know you.",
        "step1_title": "Warm-up",
        "step1_text": "The first 10 questions come from different levels and find roughly where you are.",
        "step2_title": "Adapt",
        "step2_text": "The next 10 are chosen for your level, so no time is wasted on questions that are far too easy or too hard.",
        "step3_title": "Fine-tune",
        "step3_text": "The last 8 questions sharpen the boundary between two levels.",
        "step4_title": "Result and plan",
        "step4_text": "Your level, the probabilities, sub-skills and concrete steps with weekly times.",
        "features_title": "Why this test?",
        "feat1_title": "An honest result",
        "feat1_text": "Shows level probabilities instead of a single label, and says so clearly when you are between two levels.",
        "feat2_title": "Diagnostic questions",
        "feat2_text": "Every wrong option targets a specific mistake, so you see exactly where you get stuck.",
        "feat3_title": "A personal study plan",
        "feat3_text": "The plan is tied to your weakest skills, and every step has a weekly time.",
        "feat4_title": "Retake-friendly",
        "feat4_text": "When you take the test again, questions you have seen are avoided where possible.",
        "feat5_title": "Pick up where you left off",
        "feat5_text": "Close the page and come back with the same email: the test continues where you stopped.",
        "feat6_title": "Private",
        "feat6_text": "No account, no ads, no external services. Your email is not stored; the test runs entirely locally.",
        "cefr_title": "The CEFR levels",
        "cefr_sub": "The Common European Framework describes language ability in six levels.",
        "faq_title": "Frequently asked questions",
        "footer": "A CEFR-aligned estimate, not an official exam or certificate.",
        "resume_found": "You have an unfinished test: {n} of {total} questions answered.",
        "resume_button": "Continue where I left off",
        "resume_other_browser": (
            "There is an unfinished test for this email that was started in another browser. For security it can "
            "only be continued in that browser; you can start a new test here."
        ),
        "fresh_button": "Start a new test",
        "resumed_toast": "Your test has been restored where you left off.",
        "resume_failed": "The unfinished test could not be restored (the question bank changed); a new test has started.",
        "unsure_label": "I'm not sure",
        "back_button": "Back",
        "review_button": "Review answers",
        "finish_stage_button": "Finish this part",
        "finish_test_button": "Finish the test",
        "confirm_stage": "You are finishing this part; you will not be able to return to questions {a}–{b}.",
        "confirm_test": "You are finishing the test; your answers can no longer be changed.",
        "nav_label": "Questions",
        "nav_answered": "Question {n}: answered, can be changed",
        "nav_current": "Question {n}: on screen now",
        "nav_next": "Question {n}: next question",
        "nav_locked": "Question {n}: locked, its part is finished",
        "nav_upcoming": "Question {n}: not reached yet",
        "unsure_note": "“I'm not sure” counts as wrong; a guess might be right by luck.",
        "type_cloze": "Fill the gap",
        "type_error_id": "Find the error",
        "type_reading": "Reading",
        "type_lexical_pragmatic": "Words and usage",
        "stage_1": "Warm-up",
        "stage_2": "Adapt",
        "stage_3": "Fine-tune",
        "stage_toast_2": "Warm-up done; answers to questions {a}–{b} are now locked. Questions are now chosen for your level.",
        "stage_toast_3": "Adapt done; answers to questions {a}–{b} are now locked. Last part: sharpening the boundary between two levels.",
        "timer_label": "Time",
        "no_back_note": "You can go back to questions in this part; answers lock when the part ends.",
        "result_eyebrow": "Your estimated CEFR level",
        "result_correct": "{c} / {n} correct",
        "result_time": "{minutes} min {seconds} s",
        "scale_title": "Where you are on the CEFR scale",
        "prob_title": "Level probabilities",
        "copy_title": "Share your result",
        "copy_text": "My English level test result: {level} · {group} · scaled score {score}/100 (CEFR-aligned estimate).",
        "subskill_band": "{level}",
        "subskill_hidden": "Not enough data",
        "subskill_items": "{n} questions · {pct:.0f}% correct",
        "you_are_here": "You",
    },
}
for _lang, _table in _WEB_STRINGS.items():
    STRINGS[_lang].update(_table)

# Original one-line summaries of each level for the landing page.
CEFR_SHORT: dict[str, dict[str, str]] = {
    "tr": {
        "A1": "Tanıdık kelimeler ve çok basit cümlelerle temel ihtiyaçlarını karşılar.",
        "A2": "Alışveriş, yol tarifi gibi rutin durumlarda kısa ve basit iletişim kurar.",
        "B1": "Tanıdık konulardaki açık metinleri anlar; seyahatte kendi başının çaresine bakar.",
        "B2": "Karmaşık metinlerin ana fikrini kavrar; akıcı konuşanlarla rahatça tartışır.",
        "C1": "Uzun ve zorlu metinlerdeki imaları fark eder; dili esnek ve etkili kullanır.",
        "C2": "Okuduğu hemen her şeyi rahatça anlar; en ince nüansları bile isabetle aktarır.",
    },
    "en": {
        "A1": "Meets basic needs with familiar words and very simple sentences.",
        "A2": "Communicates briefly and simply in routine situations such as shopping or directions.",
        "B1": "Understands clear texts on familiar topics and copes independently when travelling.",
        "B2": "Grasps the main ideas of complex texts and discusses comfortably with fluent speakers.",
        "C1": "Notices what long, demanding texts imply and uses the language flexibly and effectively.",
        "C2": "Understands almost anything read with ease and conveys even fine nuances accurately.",
    },
}

FAQ: dict[str, tuple[tuple[str, str], ...]] = {
    "tr": (
        ("Test ücretsiz mi, kayıt gerekiyor mu?",
         ("Evet, ücretsiz ve hesap açmanız gerekmez. E-posta yalnızca testi yeniden çözdüğünüzde farklı sorular "
         "göstermek ve yarım kalan testi geri yüklemek için kullanılır; kendisi saklanmaz.")),
        ("Sonuç nasıl hesaplanıyor?",
         ("Her sorunun zorluğu CEFR seviyelerine göre tahmin edilmiştir. Yanıtlarınızdan madde tepki kuramına "
         "dayanan bir modelle yetenek tahmini yapılır ve bu tahmin A1–C2 ölçeğine yerleştirilir. Ne kadar emin "
         "olduğumuz da ayrıca gösterilir.")),
        ("Önceki sorulara dönebilir miyim?",
         ("Evet, içinde bulunduğun bölümün içinde. Test üç bölümden oluşur (10 / 10 / 8 soru). Bir bölüm bitince "
         "seviyen yeniden hesaplanır ve sonraki sorular buna göre seçilir; bu yüzden biten bölümün cevapları "
         "kilitlenir. Bölüm sonunda «İleri»ye bastığında senden onay istenir.")),
        ("Sonuç ne kadar güvenilir?",
         ("Bu bir tahmindir. Simülasyonlarda sonuç vakaların yaklaşık %99'unda doğru seviyede ya da bir komşu "
         "seviyede çıkıyor; tam isabet yaklaşık %60. Bu yüzden olasılıkları ve sınırda olup olmadığınızı açıkça "
         "gösteriyoruz. Soru parametreleri henüz gerçek yanıtlarla kalibre edilmedi.")),
        ("«Emin değilim» ne işe yarar?",
         ("Bilmediğiniz bir soruyu tahmin etmeden geçmenizi sağlar ve yanlış sayılır. Tahmin şans eseri doğru "
         "çıkabilir; «Emin değilim» ise sonucunuzu şansa bırakmaz.")),
        ("Yarıda bırakırsam ne olur?",
         ("Yanıtlarınız kaydedilir. Aynı e-postayla döndüğünüzde kaldığınız yerden devam edebilirsiniz. En az 10 "
         "soru yanıtladıysanız «Testi bitir» ile kısmi bir sonuç da alabilirsiniz.")),
        ("Hangi beceriler ölçülüyor?",
         "Dilbilgisi, kelime bilgisi ve okuma. Dinleme, konuşma ve yazma bu sürümde ölçülmez."),
        ("CEFR nedir?",
         ("Avrupa Konseyi'nin dil yeterliliğini A1'den C2'ye altı seviyede tanımlayan ortak çerçevesidir. Okullar, "
         "işverenler ve kurslar seviyeleri çoğunlukla bu ölçekle ifade eder.")),
    ),
    "en": (
        ("Is the test free? Do I need an account?",
         ("Yes, it is free and needs no account. Your email is only used to show you different questions when you "
         "retake the test and to restore an unfinished test; the email itself is not stored.")),
        ("How is the result calculated?",
         ("Each question's difficulty has been estimated on the CEFR scale. An item response theory model turns "
         "your answers into an ability estimate, which is placed on the A1–C2 scale. How sure we are is shown "
         "as well.")),
        ("Can I go back to earlier questions?",
         ("Yes, within the part you are in. The test has three parts (10 / 10 / 8 questions). When a part ends, "
         "your level is re-estimated and the next questions are chosen from it, so that part's answers lock. "
         "You are asked to confirm before a part ends.")),
        ("How reliable is the result?",
         ("It is an estimate. In simulations the result is the right level or a neighbouring one in about 99% of "
         "cases, and exactly right in about 60%. That is why we show the probabilities and tell you when you are "
         "on a boundary. The question parameters have not yet been calibrated with real answers.")),
        ("What does “I'm not sure” do?",
         ("It lets you skip a question you don't know without guessing; it counts as wrong. A guess may be right "
         "by luck, while “I'm not sure” keeps luck out of your result.")),
        ("What if I stop halfway?",
         ("Your answers are saved. Come back with the same email to continue where you stopped. If you have "
         "answered at least 10 questions, “Finish the test” also gives you a partial result.")),
        ("Which skills are measured?",
         "Grammar, vocabulary and reading. Listening, speaking and writing are not measured in this version."),
        ("What is the CEFR?",
         ("The Council of Europe's common framework that describes language ability in six levels, A1 to C2. "
         "Schools, employers and courses usually state levels on this scale.")),
    ),
}


def t(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs: object) -> str:
    """Return the string ``key`` in ``lang``, formatted with ``kwargs``.

    Falls back to English when ``lang`` is unknown.
    """
    table = STRINGS.get(lang, STRINGS["en"])
    return table[key].format(**kwargs) if kwargs else table[key]


def level_group(level: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """Name of the CEFR user group and level, e.g. 'Independent User — Vantage'."""
    return LEVEL_GROUPS.get(lang, LEVEL_GROUPS["en"])[level]


def can_do(level: str, lang: str = DEFAULT_LANGUAGE) -> tuple[str, ...]:
    """Typical 'can do' statements for a level (original paraphrases)."""
    return CAN_DO.get(lang, CAN_DO["en"])[level]


def tag_name(tag: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """Display name of a skill tag in ``lang`` (the English tag otherwise)."""
    return TAG_NAMES.get(lang, {}).get(tag, tag)


def tag_advice(tag: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """A concrete practice step for a skill tag."""
    return TAG_ADVICE.get(lang, TAG_ADVICE["en"])[tag]


def cefr_short(level: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """One-line summary of a level for the landing page."""
    return CEFR_SHORT.get(lang, CEFR_SHORT["en"])[level]


def faq(lang: str = DEFAULT_LANGUAGE) -> tuple[tuple[str, str], ...]:
    """Question/answer pairs for the landing page."""
    return FAQ.get(lang, FAQ["en"])
