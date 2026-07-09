# Ruby Idioms

## Blocks, procs, lambdas (the core distinction)
- Block = anonymous closure passed to a method: `arr.each { |x| ... }` or multi-line `do |x| ... end`. `{}` binds tighter than `do..end` — matters in chained/ambiguous calls.
- Capture a block as param with `&`: `def run(&blk); blk.call; end`. `yield` calls the passed block without naming it; `block_given?` guards.
- **Proc vs lambda**: lambda checks arity (wrong # args → `ArgumentError`) and `return` exits only the lambda; a proc ignores extra args and `return` returns from the *enclosing method*. `->(x){ x*2 }` (lambda), `proc { |x| x*2 }` / `Proc.new`.
- `&:sym` shorthand: `%w[a b].map(&:upcase)` — `&` calls `to_proc` on the symbol. `method(:puts)` turns a method into a callable object.
- `&&.` (safe navigation): `user&.address&.city` → nil instead of NoMethodError.

## Enumerable (learn these, drop the loops)
- `map`, `select`/`filter`, `reject`, `find`/`detect`, `reduce`/`inject`, `each_with_object({})`, `flat_map`, `group_by`, `partition`, `tally`, `sum`, `min_by`/`max_by`/`sort_by`, `chunk_while`, `each_slice`, `each_cons`, `zip`, `take`/`drop`, `find_index`.
- `inject`: `nums.inject(:+)` or `nums.inject(0) { |acc, n| acc + n }`. `each_with_object` when accumulator is mutated (hash/array): `list.each_with_object({}) { |x, h| h[x.id] = x }`.
- `filter_map` (2.7): map + compact in one pass. `sum`, `count { |x| ... }`. Lazy for infinite/large: `(1..Float::INFINITY).lazy.map{...}.first(5)`.

## Symbols vs strings
- Symbols `:name` are immutable, interned (same object identity every time), fast to compare — use as hash keys, method names, enum-like flags.
- Strings are mutable, new object each literal. `"a".frozen?` false unless `# frozen_string_literal: true` magic comment (recommended top-of-file; default-ish future).
- Hash with symbol keys: `{name: "x", age: 3}` == `{:name => "x"}`. String keys need `{"k" => v}`.

## Modules & mixins
- `module M` for namespacing (`M::Klass`) and mixins. `include M` adds instance methods; `extend M` adds class/singleton methods; `prepend M` inserts *before* the class in ancestor chain (wraps methods, enables `super`).
- Ancestor lookup: `Class.ancestors` shows MRO. `super` (no parens) forwards same args; `super()` sends none.
- Comparable (define `<=>`, get `<`/`>`/`between?`), Enumerable (define `each`, get all iterators) — mix in for free behavior.

## Metaprogramming
- `define_method(:name) { |args| ... }` — create methods dynamically (closes over surrounding scope, unlike `def`).
- `method_missing(name, *args, &blk)` — intercept unknown calls; **always pair with `respond_to_missing?`** so `respond_to?`/duck-typing works.
- `send(:private_method, arg)` / `public_send` (respects visibility). `instance_variable_get/set`. `define_singleton_method`.
- `attr_accessor`/`attr_reader`/`attr_writer` generate getters/setters. `Struct.new(:a, :b)` for quick value objects. `Data.define(:a, :b)` (3.2) immutable value objects.

## Common Ruby specifics
- Everything is an expression (returns a value); last line is the implicit return. `nil` and `false` are the only falsy values (`0`, `""`, `[]` are truthy).
- `==` value equality, `equal?` identity, `eql?` value+type (hash uses `eql?`+`hash`), `===` case-equality (`when` clauses, ranges, class membership).
- Keyword args (3.0 separated from positional hash): `def f(name:, age: 0)`; `**opts` splat. `*args` positional splat.
- Ranges `(1..5)` inclusive, `(1...5)` exclusive. String interpolation `"#{expr}"` (double quotes only).

## Rails / ActiveRecord
- MVC: models (`app/models`), controllers, views; convention over configuration. `rails g model`, `rails db:migrate`.
- Query: `User.where(active: true).order(:name).limit(10)`; `find` (raises), `find_by` (nil). Lazy — executes on enumeration/`to_a`/`load`.
- Migrations: `change` method with `create_table`, `add_column`, `add_index`; reversible. `rails db:rollback`.
- Scopes: `scope :active, -> { where(active: true) }`; chainable, return relations.
- Associations: `has_many :posts`, `belongs_to :user`, `has_many :through`. Validations `validates :email, presence: true, uniqueness: true`. Callbacks `before_save`.
- Strong params: `params.require(:user).permit(:name, :email)`.

## Bundler / gems
- `Gemfile` + `bundle install` → `Gemfile.lock`. `bundle exec cmd` runs with locked versions. `gem 'rails', '~> 7.1'` (pessimistic: >=7.1, <8.0). `bundle update gem`. Gemspec for publishing.

## Idiomatic style & control flow
- Conditional modifiers: `return unless valid?`; `x = compute if needed`. `unless` = `if not` (avoid with `else`). `x ||= default` memoize/default.
- Guard clauses over nesting: `return nil if list.empty?` then main logic. Ternary `cond ? a : b`.
- Safe hash/array access: `hash.dig(:a, :b, :c)` and `array.dig(0, 1)` return nil instead of raising on missing intermediate.
- `case/when` with `===`: matches ranges (`when 1..5`), classes (`when String`), regex (`when /foo/`), lambdas. `case x in {name:}` (pattern matching, 3.0+).
- `tap { |x| ... }` for side effects returning receiver; `then`/`yield_self` for chaining transforms.
- String helpers: `%w[a b c]` (word array), `%i[a b]` (symbol array). `<<~HEREDOC` squiggly (strips indent).

## Testing & conventions
- RSpec (`describe`/`context`/`it`/`expect(x).to eq(y)`) or Minitest. `let`, `before`, factories (FactoryBot) over fixtures.
- `snake_case` methods/vars, `CamelCase` classes, `SCREAMING_SNAKE` constants. `?` predicate methods (`empty?`), `!` bang mutating/raising (`sort!`, `save!`).
- `require_relative` for local files; `require` for gems/load path.

## Gotchas -> Fix
- **N+1 queries**: `users.each { |u| u.posts.count }` fires 1+N queries -> `User.includes(:posts)` (eager load) or `preload`/`eager_load`.
- Proc `return` returns from enclosing method (surprise early exit) -> use lambda if you need local return semantics.
- Mutable default args / shared state: `def f(a = [])` reuses... actually re-evaluated each call in Ruby (safe), BUT constants and class vars are shared — `CONST = []` then `CONST << x` mutates the shared array. `freeze` constants.
- String mutation aliasing: `b = a; b << "x"` mutates `a` too (same object) -> `a.dup` or frozen strings.
- `&&`/`||` return operands not booleans: `a || b` returns `b` when `a` falsy -> fine for defaults `x = opt || default`, but `0 || 5` = 0 (0 truthy, unlike JS).
- `nil.to_s` = `""`, `nil.to_a` = `[]` (silent) — can mask bugs; check explicitly with `.nil?` when it matters.
- Integer division: `5 / 2 == 2` (floors); use `5.0 / 2` or `5.fdiv(2)` for float.
- `hash[:missing]` returns `nil` not error; `hash.fetch(:k)` raises, `fetch(:k, default)` or `Hash.new(default)`.
- Class variables `@@var` shared across subclasses (leaky inheritance) -> prefer class instance variables `@var` at class level.
- Modifying collection while iterating raises/undefined -> iterate a `.dup` or build a new array with `map`/`reject`.
- Rails `update` skips validations? No — `update` runs them; `update_column`/`update_all` SKIP validations + callbacks (raw SQL). Know which you called.
- `save` returns false silently on validation failure; use `save!`/`create!` to raise, or check the boolean + `.errors`.
- `default_scope` leaks into every query (incl. joins/associations) — avoid; use named scopes.
- Time zones: use `Time.zone.now`/`Time.current` (Rails) not `Time.now` (system zone) to respect app TZ.
