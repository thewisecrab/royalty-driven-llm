# شرح RDLLM

## ELI5

تخيل أن إجابة الذكاء الاصطناعي مثل تقرير مدرسي. RDLLM يجعل النظام يوضح ما
المصادر التي استخدمها، وأي جملة يدعمها أي مصدر، وهل يجب أن يحصل أصحاب تلك
المصادر على attribution أو payment. إذا كان الدليل ناقصا، فلا يجب أن تظهر
الإجابة كأنها موثقة بالكامل.

## Simple

RDLLM طبقة open-source لمنتجات الذكاء الاصطناعي. تضيف source footer ظاهر
للإجابة، وتتحقق من أن المصادر تدعم claims فعلا، وتسجل كيف يرتبط source usage
بالـ payout أو escrow.

استخدمها عند بناء chatbot أو RAG app أو search assistant أو agent أو model API
أو marketplace أو creator platform وتريد أن يرى المستخدمون من أين جاءت
الإجابة.

## Non-Technical

RDLLM يساعد ثلاث فئات:

- المستخدمون يرون sources و Claim Evidence و confidence signals بدلا من إجابة
  AI مجردة.
- creators و publishers يحصلون على attribution evidence و settlement records.
- operators يحصلون على verification gates قبل عرض الإجابة كـ grounded أو
  royalty-bearing.

النظام لا يدعي أنه يقرأ أفكار النموذج المخفية. هو يعرض أدلة قابلة للملاحظة:
visible source support و answer-source overlap و Claim Evidence و
source-disagreement checks و payout allocation.

## Technical

في runtime يأخذ RDLLM answer و source references و revenue context. ثم يبني
source footer يحتوي على source rows و Claim Evidence rows. كل claim row يحتوي
على claim hash و support score و evidence span hash و character offsets و
evidence preview و warrant status و source-disagreement status و source label.

قبل العرض، يعيد verifiers حساب display hash و footer hash و row hashes و source
usage metrics و Claim Evidence و citation markers و answer links و
claim-source closure و model-reliance wording و attribution-gap closure و source
disagreement. تصبح الإجابة public-facing فقط عندما تكون
`production_display_ready` true و `source_grounding_acceptance` passed.

للبدء في التنفيذ:

- [Quickstart](quickstart.md)
- [GitHub Start Here](../../github_start_here.md)
- [Live use cases](../../../examples/live_use_cases/README.md)
- [API client examples](../../../examples/api_clients/README.md)
