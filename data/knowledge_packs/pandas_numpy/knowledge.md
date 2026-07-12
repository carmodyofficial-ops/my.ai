# pandas + NumPy — Data-Science Quick Reference

## NumPy: ndarray core
- Homogeneous N-d array, single `dtype` (`a.dtype`, `a.shape`, `a.ndim`, `a.size`). Contiguous memory + strides → fast. Set/cast: `np.array(x, dtype=np.float64)`, `a.astype(int)`.
- **VECTORIZE**: operate on whole arrays — `a + b`, `a * 2`, `np.sqrt(a)`, `np.where`. A Python `for` over elements is 10–100× slower and misses SIMD. Reductions release nothing to interpreter.
- Create: `np.zeros((3,4))`, `np.ones`, `np.full`, `np.arange(10)`, `np.linspace(0,1,5)`, `np.eye`, `np.random.default_rng().random(3)`.
- dtypes matter: `int64` overflows silently (no promotion to bignum); `float64` NaN-capable; downcast to `float32`/`int32` to halve memory.

## Broadcasting
- Align shapes from the **trailing** dim; each pair must be equal or one is 1 (stretched, no copy). Missing leading dims count as 1.
- `(3,1) + (1,4) -> (3,4)`. `(n,3) - (3,) -> (n,3)`. Incompatible (`(3,)` vs `(4,)`) raises. Add an axis with `a[:, None]` to force a column and enable an outer-style op.

## Views vs copies (GOTCHA)
- Basic slicing returns a **view**: `b = a[1:4]; b[0]=99` mutates `a`. Detach with `.copy()`.
- Fancy indexing (`a[[0,2]]`) and boolean indexing (`a[mask]`) return **copies**.
- `a.reshape`/`a.ravel` view when possible; `a.flatten` always copies. `.base is not None` hints it's a view.

## Axes & reductions
- `axis=0` collapses **rows** → per-column result; `axis=1` collapses **columns** → per-row. No axis → scalar over all.
- `a.sum(axis=0)`, `a.mean(axis=1)`, `min/max/std/argmax/cumsum`. NaN-safe variants: `np.nansum`, `np.nanmean`.
- Reshape `a.reshape(2,-1)` (-1 infers), transpose `a.T`, concat `np.concatenate`, stack `np.vstack`/`np.hstack`.

## NumPy indexing
- Boolean mask `a[a>0]`; combine with `&`/`|`/`~` and **parens** `a[(a>0)&(a<5)]` (Python `and`/`or` fail on arrays).
- Fancy `a[[0,2,4]]`, 2-D `a[rows, cols]`. `np.where(cond, x, y)` elementwise select; `np.where(cond)` → index tuple.

## pandas: structures
- `Series` = 1-D labeled (values + Index); `DataFrame` = 2-D, columns each a Series with own dtype. The **Index** drives alignment.
- IO: `pd.read_csv('f.csv', dtype=..., parse_dates=[...])`, `df.to_csv('f.csv', index=False)`, `read_parquet` (typed, fast), `read_json`.

## Selection — `.loc`/`.iloc`, not chained `[][]`
- `df.loc[rowlabel, 'col']` label-based, **inclusive** slice; `df.iloc[0:5, 2]` position-based, exclusive.
- Column `df['x']`; rows by mask `df[df.x>0]`; combined `df.loc[df.x>0, 'y']`. `df.at[i,'c']`/`.iat` fast scalar access.
- Integer-labeled index: `df.loc[5]` (label 5) ≠ `df.iloc[5]` (6th row).

## groupby / agg / transform
- Split-apply-combine: `df.groupby('k')['v'].mean()`, `.agg({'v':'mean','n':'sum'})`, named `.agg(avg=('v','mean'))`.
- `transform` returns same-shape (broadcast back for per-group normalization): `df['z']=df.groupby('k')['v'].transform('mean')`. `filter` drops whole groups. `apply` most general (slowest).
- `observed=True` for categorical keys (skip empty combos); `dropna=False` to keep NaN keys; `as_index=False` to keep key as a column.

## Merge / join / concat / reshape
- `pd.merge(a, b, on='id', how='inner'|'left'|'outer'|'right')`; `validate='1:m'` catches unexpected fan-out; `indicator=True` shows match source.
- `a.join(b)` merges on index. `pd.concat([a,b])` stack rows (`axis=0`) or cols (`axis=1`) — aligns on the other axis' index.
- Reshape: `df.pivot_table(index=,columns=,values=,aggfunc=)` (aggregates dups), `pivot` (no agg, errors on dups), `melt` (wide→long), `stack`/`unstack`.

## Missing data & dtypes
- `df.isna()`, `df.fillna(0)`/`ffill()`/`bfill()`, `df.dropna(subset=['x'])`.
- NaN is float → propagates through arithmetic, breaks int dtype → use nullable `Int64`/`boolean`/`string` (pandas NA). `category` dtype for low-cardinality strings (huge memory + groupby speed win).

## Vectorized accessors, datetime, perf
- Strings: `df.s.str.lower()`, `.str.contains('a')`, `.str.split`, `.str.extract(r'(\d+)')`.
- Datetime: `pd.to_datetime(df.d)` then `df.d.dt.year`, `.dt.dayofweek`, `.dt.floor('D')`; set a `DatetimeIndex` for `.resample('W').sum()` and `.rolling(7).mean()`. Store tz-aware for correctness.
- Prefer built-in vectorized ops > `.apply` (Python loop under the hood) > `iterrows` (slowest). Method chaining with `.pipe`/`.assign`/`.query` keeps it readable and copy-free.

## Combine, window, performance
- `df.query('a>0 and b=="x"')` and `df.eval('c = a+b')` — terse, and on large frames use the numexpr engine (less memory, faster). `@var` refers to Python locals inside `query`.
- Sort `df.sort_values(['a','b'], ascending=[True,False])`; rank `df.rank()`; `nlargest(5,'v')` beats sort+head.
- `df.duplicated()`/`drop_duplicates(subset=, keep='last')`; `pd.cut`/`qcut` binning; `crosstab`; `df.pipe(fn)` for chainable custom steps.
- Memory: `df.info(memory_usage='deep')`, downcast with `pd.to_numeric(s, downcast='integer')`, load only needed `usecols`, chunk huge CSVs with `chunksize=`. Parquet preserves dtypes and is far faster than CSV.

## GOTCHAS → Fix
- **SettingWithCopyWarning**: `df[df.x>0]['y']=1` writes to a temporary copy, silently no-ops → single `df.loc[df.x>0,'y']=1`.
- **Chained indexing** `df['a']['b']` may read a copy → use `.loc[row, col]`.
- **View vs copy ambiguity** when slicing then assigning → `.copy()` to be explicit.
- **`inplace=True`** rarely faster, breaks chaining, being deprecated in spots → reassign `df = df.dropna()`.
- **`.apply` slowness** → replace with vectorized ops / `np.where` / `.map` / groupby-transform.
- **Index-alignment surprises**: arithmetic between two Series aligns on index (mismatched labels → NaN) → `.reset_index(drop=True)` or `.to_numpy()` to drop labels.
- **`object` dtype** kills performance and hides mixed types → cast to numeric/`category`/`string`.
- **Boolean masks with `and`/`or`** raise or mislead → use `&`/`|`/`~` with parentheses.
- **Float equality / NaN != NaN** → use `np.isclose` and `.isna()`, never `== np.nan`.
- **Silent int overflow** in NumPy and lost precision on huge `read_csv` ids → set explicit `dtype`/`Int64`/`str`.
- **`concat` in a loop** is O(n²) → collect into a list, one `pd.concat` at the end.
