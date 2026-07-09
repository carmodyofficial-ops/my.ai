# R Language

## Vectors, the atom of R
- Everything is a vector; scalars are length-1 vectors. `c(1, 2, 3)` combines. Atomic types: `logical`, `integer` (`1L`), `double`, `character`, `complex`. `c()` coerces to the most general type (logical < integer < double < character).
- **1-indexed**: `x[1]` is first, `x[length(x)]` is last (no negative-from-end; `x[-1]` *removes* element 1). `x[c(1,3)]`, `x[x > 5]` (logical mask), `x[-c(1,2)]` (drop).
- Vectorized arithmetic: `x + y`, `x * 2`, `sqrt(x)` — operate element-wise, no loops. **Recycling**: shorter vector repeats to match longer (`c(1,2,3,4) + c(10,20)` → `11 22 13 24`); warns only if lengths aren't multiples.
- `seq(1, 10, by = 2)`, `seq_len(n)`, `seq_along(x)` (safe for loops — `1:length(x)` breaks when length 0), `rep(x, times/each)`.
- Names: `v <- c(a = 1, b = 2)`; `v["a"]`. `NULL` = absent (length 0), removes list elements.

## Data frames & lists
- `list()` holds mixed types; `df$col`, `df[["col"]]` extract a column (vector); `df["col"]` returns a 1-col data frame. `df[rows, cols]` (2D). `df[df$age > 30, ]` (keep the comma).
- Data frame = list of equal-length columns. `data.frame(...)` (default `stringsAsFactors = FALSE` since R 4.0). `nrow`, `ncol`, `names`, `str(df)`, `summary(df)`, `head(df)`.
- tibbles (`tibble()`) = tidyverse data frames: never coerce strings to factors, don't partial-match names, print cleanly.

## Tidyverse: dplyr + the pipe
- Native pipe `|>` (R 4.1+) or magrittr `%>%`. `x |> f() |> g()` = `g(f(x))`.
- dplyr verbs (operate on data frames, return data frames):
```r
df |>
  filter(age > 30, city == "NYC") |>
  mutate(bmi = weight / height^2) |>
  group_by(dept) |>
  summarise(mean_sal = mean(salary, na.rm = TRUE), n = n()) |>
  arrange(desc(mean_sal)) |>
  select(dept, mean_sal)
```
- `filter` (rows by condition), `select` (columns), `mutate` (new/changed cols), `arrange` (sort, `desc()`), `summarise` (aggregate), `group_by`, `slice`, `distinct`, `rename`, `left_join`/`inner_join(a, b, by = "id")`, `count()`, `across(cols, fn)`.
- tidyr reshaping: `pivot_longer` (wide→long), `pivot_wider` (long→wide), `separate`, `unite`, `drop_na`, `fill`. "Tidy data" = one row per observation, one column per variable.

## ggplot2 (grammar of graphics)
- Layered, `+` to add (not `|>`): `ggplot(df, aes(x = wt, y = mpg, color = cyl)) + geom_point() + geom_smooth(method = "lm") + facet_wrap(~gear) + labs(title = "...") + theme_minimal()`.
- `aes()` maps data→visual; set constants *outside* aes (`geom_point(color = "red")` vs mapping a column inside). Geoms: `geom_point/line/bar/col/histogram/boxplot/tile`. `scale_*`, `coord_*`, `facet_grid/wrap`.

## apply family vs loops
- Prefer vectorized ops and `apply` family over `for` (which is fine but often slower and verbose): `sapply` (simplify to vector/matrix), `lapply` (always list), `vapply` (type-safe, specify `FUN.VALUE`), `mapply` (multiple args), `apply(m, 1|2, fn)` (matrix rows/cols), `tapply` (grouped), `Map`/`Reduce`/`Filter`.
- purrr equivalents: `map()`, `map_dbl()`, `map_chr()`, `map2()`, `pmap()`, `imap()` — type-stable, `~ .x + 1` formula shorthand.
- Preallocate if you must loop: `out <- vector("numeric", n); for (i in seq_len(n)) out[i] <- ...` — growing `out <- c(out, x)` is O(n²).

## Factors
- Categorical with fixed `levels`: `factor(c("lo","hi","lo"), levels = c("lo","hi"))`. Stored as integers + a levels attribute. Ordered factors `ordered = TRUE` for `<` comparisons.
- Control level order (affects plots/models/reference level). `forcats` (`fct_reorder`, `fct_relevel`, `fct_lump`) manages them cleanly.

## Statistical modeling
- Formula interface `y ~ x1 + x2 + x1:x2` (`:` interaction, `*` main+interaction, `.` all others, `-1` no intercept).
- `lm(mpg ~ wt + hp, data = df)` linear; `glm(y ~ x, family = binomial, data = df)` logistic. Inspect with `summary(model)`, `coef`, `confint`, `predict(model, newdata)`, `residuals`, `anova`. `broom::tidy(model)` → tidy data frame.
- `t.test`, `cor`, `aov`, `lme4::lmer` (mixed). `set.seed(n)` before any random draw for reproducibility.

## Packages
- `install.packages("dplyr")`; `library(dplyr)` loads (attaches). `pkg::fun()` calls without attaching. CRAN, Bioconductor, `remotes::install_github()`. `renv` for project-locked dependencies.

## Matrices, functions, control flow
- Matrix `matrix(1:6, nrow = 2)`; `%*%` matrix multiply, `t()` transpose, `solve()` inverse, `dim()`. Arrays are n-dimensional. `data.frame` for mixed types, `matrix` for homogeneous numeric.
- Functions: `f <- function(x, y = 1) { x + y }`; last expression is the return (explicit `return()` for early exit). `...` passes extra args through. Default args can reference earlier args. Lexical scoping; `<<-` assigns to enclosing/global scope.
- Anonymous fns: `\(x) x^2` (R 4.1+) or `function(x) x^2`. Control flow `if/else`, `for (i in x)`, `while`, `repeat`+`break`, `next` (continue). `switch(type, a = 1, b = 2)`.

## I/O, dates, environment
- Read: `read.csv()`, `readr::read_csv()` (faster, typed), `readxl::read_excel()`, `readRDS`/`saveRDS` (native binary). Write with `write.csv(df, row.names = FALSE)`.
- Dates: `Sys.Date()`, `as.Date("2026-07-09")`, lubridate (`ymd()`, `mdy()`, `%m+% months(1)`). `Sys.time()` POSIXct for timestamps.
- Missing types: `NA` (missing), `NULL` (absent/empty), `NaN` (0/0), `Inf`/`-Inf`. `is.na`, `is.null`, `is.finite`, `complete.cases(df)`.

## Gotchas -> Fix
- **1-indexing** and `x[-1]` removes (not last element) — off-by-one from other languages; last is `x[length(x)]` / `tail(x, 1)`.
- **NA propagates**: `mean(c(1, NA, 3))` = `NA`; `sum(x, na.rm = TRUE)`, `mean(x, na.rm = TRUE)`. Test with `is.na(x)` — **never** `x == NA` (returns `NA`). `NA` is typed (`NA_integer_`, etc.).
- **Recycling silent bugs**: mismatched lengths recycle without error if multiples — check lengths; a stray recycle corrupts results quietly.
- **Factor→number trap**: `as.numeric(factor)` returns the integer *codes*, not the labels. Use `as.numeric(as.character(f))` to recover numeric labels.
- `stringsAsFactors`: default FALSE since R 4.0 — old code assuming TRUE breaks; be explicit.
- `1:0` gives `c(1, 0)` not empty — `for (i in 1:length(x))` runs once on empty `x`. Use `seq_len(length(x))` / `seq_along(x)`.
- `sapply` returns unpredictable type (vector, matrix, or list depending on results) — use `vapply` (declare output) or purrr `map_*` for type safety.
- `df[, "col"]` drops to a vector when one column; `df[, "col", drop = FALSE]` keeps a data frame. tibbles never drop.
- `<-` vs `=`: use `<-` for assignment; `=` also works but conflates with named args inside calls. `->` assigns rightward.
- Floating point: `0.1 + 0.2 == 0.3` is FALSE -> `all.equal(a, b)` or `isTRUE(all.equal(...))`.
- Partial matching of `$` on lists/args (`df$na` matches `name`) — silent; tibbles/`[[` disable it.
- Vectorized `ifelse(cond, a, b)` (element-wise, returns vector) vs `if(cond) a else b` (scalar, control flow) — don't confuse.
- `T`/`F` are just variables (can be reassigned!) — always write `TRUE`/`FALSE`.
- Lazy argument evaluation + `<<-` (global assign) and copy-on-modify semantics surprise — R copies on write; large-object loops can blow memory.
