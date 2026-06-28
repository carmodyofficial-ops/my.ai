# pandas + NumPy — Data-Science Quick Reference

## NumPy: ndarray core
- Homogeneous N-d array, single `dtype` (`a.dtype`, `a.shape`, `a.ndim`). Set type: `np.array(x, dtype=np.float64)`, `a.astype(int)`.
- VECTORIZE: operate on whole arrays — `a + b`, `a * 2`, `np.sqrt(a)`. NEVER loop over elements in Python; loops are 10-100x slower.
- Create: `np.zeros((3,4))`, `np.ones`, `np.arange(10)`, `np.linspace(0,1,5)`, `np.random.rand(3)`.

## Broadcasting
- Align shapes from the TRAILING dim; dims must be equal or one is 1 (stretched). Missing leading dims treated as 1.
- `(3,1) + (1,4) -> (3,4)`. `a (n,3) - mean (3,) -> (n,3)`. Mismatch (e.g. `(3,)` vs `(4,)`) raises.

## Views vs copies (GOTCHA)
- Basic slicing returns a VIEW: `b = a[1:4]; b[0]=99` mutates `a`. Detach with `a[1:4].copy()`.
- Fancy/boolean indexing returns a COPY.

## Axes & reductions
- `axis=0` collapses ROWS (down columns -> per-column result); `axis=1` collapses COLUMNS (across -> per-row).
- `a.sum(axis=0)`, `a.mean(axis=1)`, also `min/max/std/argmax`. No axis -> over all elements.
- `a.reshape(2,-1)` (-1 infers), `a.T`, `a.ravel()`.

## Indexing
- Boolean mask: `a[a>0]`, combine with `&`/`|` and parens: `a[(a>0)&(a<5)]`.
- `np.where(cond, x, y)` elementwise select; `np.where(cond)` returns indices.

## pandas: structures
- `Series` = 1-D labeled; `DataFrame` = 2-D labeled columns (each a Series, own dtype).
- IO: `pd.read_csv('f.csv')`, `df.to_csv('f.csv', index=False)`. Also `read_parquet`/`read_json`.

## Selection — use `.loc`/`.iloc`, not chained `[][]`
- `df.loc[rowlabel, 'col']` label-based (inclusive); `df.iloc[0:5, 2]` position-based.
- Column: `df['x']`; rows by mask: `df[df.x>0]`; combine: `df.loc[df.x>0, 'y']`.
- Integer-label index: `df.loc[5]` (label 5) vs `df.iloc[5]` (6th row) differ — don't confuse.

## Transform & aggregate
- `df.groupby('k').agg({'v':'mean','n':'sum'})` or `.groupby('k')['v'].mean()`.
- `pd.merge(a, b, on='id', how='inner')` (or `left`/`outer`/`right`); `a.join(b)` joins on index.
- `df.assign(z=df.x+df.y)` returns new frame. `value_counts()`, `pivot_table(index=,columns=,values=,aggfunc=)`.

## Missing data
- `df.isna()`, `df.fillna(0)` / `fillna(method='ffill')`, `df.dropna(subset=['x'])`.
- NaN is float; propagates through arithmetic; breaks int dtype (use nullable `Int64`).

## Vectorized accessors
- Strings: `df.s.str.lower()`, `.str.contains('a')`, `.str.split`, `.str.replace`.
- Datetime: `pd.to_datetime(df.d)` then `df.d.dt.year`, `.dt.dayofweek`.
- `apply`/`iterrows` only as last resort — vectorize first.

## GOTCHAS + fixes
- **SettingWithCopyWarning**: `df[df.x>0]['y']=1` silently fails — use `df.loc[df.x>0,'y']=1`.
- **`iterrows` is SLOW**: replace with vectorized ops or `np.where`.
- **Slice mutation**: editing a returned slice may/may not hit original — `.copy()` to be safe.
- **`object` dtype kills perf**: cast to numeric/`category` (`df.c.astype('category')`).
