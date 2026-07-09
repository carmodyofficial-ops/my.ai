# NLP Engineering

## Text preprocessing
- Steps: Unicode normalize (NFC/NFKC), lowercasing (task-dependent — hurts NER/casing), strip/normalize whitespace, handle URLs/emojis/mentions, contraction expansion.
- Classic (pre-transformer): tokenize on whitespace/regex, stopword removal, stemming (Porter — crude, `running→run`) vs lemmatization (dictionary, POS-aware, `better→good`).
- **Modern transformers**: DON'T aggressively clean — subword tokenizers handle casing/rare words; over-cleaning removes signal (punctuation, case). Just normalize + truncate.

## Tokenization
- **Word-level**: huge vocab, OOV problem. **Char-level**: tiny vocab, long sequences.
- **Subword** (standard): balances vocab size + OOV. Rare words split into pieces.
  - **BPE**: iteratively merge most frequent adjacent pair (GPT, RoBERTa). Byte-level BPE (GPT-2) handles any Unicode via bytes.
  - **WordPiece**: BERT; merges by likelihood; `##` marks continuation (`playing→play ##ing`).
  - **Unigram/SentencePiece**: probabilistic, language-agnostic (no pre-tokenization), `▁` marks word start (T5, LLaMA, mBERT).
- Special tokens: `[CLS]`,`[SEP]`,`[PAD]`,`[MASK]`,`[UNK]`,`<s>`,`</s>`,`<pad>`,`<|endoftext|>`.
- Output: `input_ids`, `attention_mask` (1=real,0=pad), `token_type_ids` (segment). Always use the SAME tokenizer as the pretrained model.

## Embeddings
- **Static**: word2vec (skip-gram/CBOW, negative sampling), GloVe (co-occurrence factorization), fastText (subword — handles OOV). One vector per word → no polysemy (`bank` fixed).
- **Contextual**: ELMo (biLSTM) → BERT/GPT (transformer) — vector depends on sentence context; same word, different vectors.
- Cosine similarity for semantic closeness; used for retrieval, clustering, RAG. Sentence-level: mean-pool tokens or use Sentence-BERT.

## Classic tasks
- **Text classification / sentiment**: doc → label. Baselines: TF-IDF + logistic/SVM/NB; modern: fine-tune BERT `[CLS]`.
- **NER** (token classification): tag each token `B-PER/I-PER/O` (BIO/BIOES). Needs alignment of labels to subword tokens.
- **POS tagging, dependency parsing, coreference**.
- **Seq2seq**: translation, summarization, QA — encoder-decoder.

## Sequence models → transformers
- RNN/LSTM/GRU: sequential, struggle with long-range deps + no parallelism.
- **Attention** removed the bottleneck: `softmax(QKᵀ/√dₖ)V`, every token attends to all. **Transformer** (encoder-decoder) is the backbone.
- **Encoder-only** (BERT, RoBERTa, DeBERTa): bidirectional, masked-LM pretrain → classification/NER/embeddings.
- **Decoder-only** (GPT, LLaMA, Mistral): causal LM (next-token) → generation, few-shot, chat.
- **Encoder-decoder** (T5, BART, mT5): text-to-text → translation, summarization.

## Pretraining + fine-tuning
- Pretrain on massive unlabeled text (MLM for BERT: predict 15% masked; CLM for GPT: next token).
- **Fine-tune**: add task head, train on labeled data (LR 1e-5 to 5e-5, 2–4 epochs, warmup, AdamW). Full fine-tune vs **PEFT** (LoRA/adapters — freeze base, train small deltas — cheap, avoids catastrophic forgetting).
- **Prompting / in-context learning**: zero/few-shot with decoder LLMs, no weight updates.
- Instruction tuning + RLHF/DPO align chat models.

## Evaluation
- **Classification/NER**: precision/recall/F1 (macro vs micro; entity-level F1 for NER, not token-level), accuracy.
- **Generation**: **BLEU** (n-gram precision + brevity penalty; translation), **ROUGE** (recall of n-grams/LCS; summarization — ROUGE-1/2/L), METEOR, chrF.
- **Perplexity** `exp(mean CE loss)` — LM quality, lower better; only comparable within same tokenizer/vocab.
- Semantic: BERTScore, embedding cosine. LLM outputs: human eval / LLM-as-judge.
- Retrieval/RAG: recall@k, MRR, nDCG.

## Long text
- Transformer self-attention is `O(n²)` in length; models have fixed max context (BERT 512, many LLMs 4k–128k+).
- Strategies: truncate (head/tail), **sliding window + stride** (chunk with overlap), hierarchical (encode chunks → aggregate), efficient attention (Longformer/BigBird sparse, FlashAttention for speed/memory), retrieval (RAG — fetch relevant chunks). For QA use overlapping windows so answers aren't split.

## Multilingual
- mBERT, XLM-R, mT5 share subword vocab across languages → zero-shot cross-lingual transfer.
- SentencePiece avoids language-specific pre-tokenization. Watch tokenization inefficiency for non-Latin scripts (more tokens/word → higher cost, shorter effective context).

## Classic feature representations
- **Bag-of-words**: token counts; ignores order. **TF-IDF**: `tf·log(N/df)` down-weights common words → strong sparse baseline with linear/SVM/NB.
- **n-grams** (bi/tri) capture local order; hashing trick for huge vocab. Char n-grams robust to typos.
- These remain competitive + cheap for small labeled datasets and topic/spam classification.

## Vocabulary + OOV
- Fixed vocab from training corpus; rare words → `[UNK]` (word-level) or split into subwords (BPE/WordPiece — no true OOV, just more pieces).
- Handle numbers/dates/URLs with normalization or special tokens. Vocab size trades sequence length vs granularity (typical 30k–50k subwords; LLMs 32k–256k).

## Fine-tuning recipe (HF Transformers)
- Load `AutoTokenizer` + `AutoModelForSequenceClassification.from_pretrained(ckpt, num_labels=k)`.
- Tokenize with `truncation=True, max_length=..., padding` (dynamic pad via `DataCollatorWithPadding`).
- `Trainer`/`TrainingArguments`: `lr=2e-5`, `epochs=3`, warmup, weight decay 0.01, `fp16/bf16`, eval each epoch, `load_best_model_at_end` on val F1.
- Freeze lower layers or use **LoRA** (PEFT) for large models / limited compute. Set the head's dropout; watch catastrophic forgetting.

## Decoding (generation)
- **Greedy** (argmax) → repetitive; **beam search** (translation/summarization) keeps top-`b` sequences.
- **Sampling**: temperature `T` (lower=sharper), **top-k**, **top-p (nucleus)** for open-ended text. Repetition penalty / no-repeat n-gram to curb loops.
- Set `max_new_tokens`, `eos_token_id`; left-pad for batched decoder-only generation.

## RAG + embeddings retrieval
- Chunk docs (overlap), embed with sentence encoder, index in a vector store (FAISS/HNSW), retrieve top-k by cosine, feed as context to an LLM.
- Quality hinges on chunking, embedding model, and retrieval recall. Re-rank (cross-encoder) for precision. Evaluate recall@k, faithfulness/groundedness.

## Data + labeling
- Deduplicate + normalize; split by document/author/time to avoid leakage. Measure class balance.
- Weak/semi-supervision (Snorkel, rules) bootstraps labels; active learning targets uncertain samples. Track inter-annotator agreement (Cohen's κ).
- Stratify splits by label; keep a frozen test set. Beware domain shift (train news, deploy tweets).

## Core NLP tasks quick map
- **Classification/sentiment**: doc→label; fine-tune encoder `[CLS]` or TF-IDF+linear.
- **Token classification (NER/POS)**: label per subword, BIO scheme, entity-level F1.
- **QA extractive**: predict answer span start/end logits over context (SQuAD-style).
- **Seq2seq**: translation/summarization/paraphrase (T5/BART); generation metrics.
- **Retrieval/semantic search**: bi-encoder embeddings + ANN index; re-rank with cross-encoder.
- **Language modeling**: next-token (GPT) → generation, few-shot, chat.

## Transformer families cheat sheet
- **BERT/RoBERTa/DeBERTa/ELECTRA** (encoder): understanding, embeddings, classification, NER. Bidirectional, MLM pretrain.
- **GPT/LLaMA/Mistral/Qwen** (decoder): generation, chat, in-context learning. Causal LM.
- **T5/BART/mT5/FLAN-T5** (enc-dec): text-to-text, summarization, translation.
- **Sentence-BERT / E5 / BGE**: sentence embeddings for retrieval/similarity.
- Distilled/small (DistilBERT, MiniLM) trade a little accuracy for speed/size.

## Handling long documents (detail)
- Fixed context windows (BERT 512 tokens). Options: truncate head/tail, sliding window with stride + aggregate, hierarchical encoding (chunk → pool), long-context models (Longformer/BigBird sparse attention, FlashAttention for speed), or RAG retrieval of relevant chunks.
- For QA/NER, use overlapping windows so entities/answers aren't split at boundaries; merge predictions.

## Practical fine-tuning knobs
- LR 1e-5–5e-5 (lower for large models), 2–4 epochs, warmup 6–10%, weight decay 0.01, AdamW, gradient clipping 1.0, fp16/bf16.
- Batch by token budget; dynamic padding; early stop on val macro-F1. PEFT/LoRA freezes base weights, trains low-rank adapters (rank 8–64) — cheap, avoids forgetting.
- Watch overfitting on small data: freeze lower layers, dropout, augment (back-translation, synonym replace, EDA).

## Multilingual + tokenization economy
- Shared subword vocab (XLM-R, mBERT, mT5) → zero-shot cross-lingual transfer. SentencePiece removes language-specific pre-tokenization.
- Non-Latin/low-resource scripts fragment into more tokens → higher cost, shorter effective context, potential quality gap. Consider language-specific or byte-level tokenizers.

## Pitfalls -> Fix
- **Tokenizer ≠ model** (mismatched vocab) -> load tokenizer from the exact same checkpoint as the model.
- **Fine-tuned on cleaned text, inference on raw** (distribution mismatch) -> identical preprocessing train + inference.
- **NER labels not aligned to subwords** -> map word labels to first subword, set others to -100 (ignore in loss).
- **Data leakage** (duplicate/near-dup docs, or same author/thread across train/test) -> dedupe + group split.
- **Label noise / inconsistent annotation** -> measure inter-annotator agreement, clean or model as noisy.
- **Truncation silently dropping the answer** -> log truncation rate; use sliding windows for long docs.
- **Token-level F1 inflating NER scores** -> report entity/span-level F1 (seqeval).
- **BLEU/ROUGE compared across different tokenization/normalization** -> fix a canonical scorer (sacreBLEU).
- **Perplexity compared across different tokenizers** -> not comparable; only within same vocab.
- **Class imbalance in classification** -> weighted loss, macro-F1, resample.
- **Ignoring attention_mask / wrong padding side** -> pad correctly; decoder-only models often need left-padding for batched generation.
- **Test-set contamination in pretrained LLM** -> beware benchmark leakage when evaluating.
- **Casing/accents lost by over-normalization** -> keep case for NER/QA.
- **Prompt injection in user text** (LLM apps) -> sanitize/delimit untrusted input, don't concatenate blindly.
