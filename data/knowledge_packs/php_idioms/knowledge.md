# PHP Idioms (PHP 8+)

## Types & modern syntax you should reach for first
- `declare(strict_types=1);` at top of every file — makes scalar type hints reject silent coercion (`int` param won't accept `"5"`). Without it, weak mode coerces.
- Typed properties: `private int $count = 0;`; nullable `?string`; union `int|string`; intersection `Countable&Iterator`; `mixed`, `never`, `void`, `static`, `false`, `null`.
- Constructor promotion collapses field decl + assign: `function __construct(private readonly int $id, public string $name = '') {}`.
- `readonly` properties (8.1) — write once (from inside class scope), then immutable; `readonly class` (8.2) makes all props readonly.
- Enums (8.1): `enum Suit: string { case Hearts = 'H'; ... }` — backed by scalar. `Suit::Hearts->value`, `Suit::from('H')` (throws), `Suit::tryFrom('X')` (null), `Suit::cases()`. Enums can have methods + implement interfaces; no instances/state.
- `match` (8.0) — strict `===` compare, no fallthrough, returns value, exhaustive (`\UnhandledMatchError` if no arm): `match($x) { 1, 2 => 'a', default => 'b' }`. Prefer over `switch` (loose `==`, fallthrough, no return).
- Named args: `htmlspecialchars($s, double_encode: false)` — skip optional middle params; order-independent after positionals.
- Nullsafe: `$user?->address?->city` short-circuits to null. Null coalescing `$a ?? 'def'`; assign `$a['k'] ??= 'def'`.
- First-class callable (8.1): `$fn = strlen(...)`, `$m = $obj->method(...)`.
- Attributes (8.0): `#[Route('/users', methods: ['GET'])]` — read via Reflection; replaces docblock annotations.
- Fibers (8.1): cooperative multitasking primitive (`Fiber::suspend`/`resume`); low-level, underpins ReactPHP/Amp async, not for daily use.

## Arrays (the workhorse)
- Ordered maps, not real arrays: `[1, 2]` (list) and `['k' => 'v']` (assoc) are the same type. `array_is_list($a)` checks sequential 0..n keys.
- **Copy-on-write, value semantics**: `$b = $a` copies; mutating `$b` doesn't touch `$a`. Pass to function copies unless `&$ref`. Objects are handle-by-value (mutations shared, but `$b = $obj` copies the handle not the object).
- Functional: `array_map`, `array_filter` (preserves keys — `array_values` to reindex), `array_reduce`, `array_column`, `array_combine`, `array_flip`, `array_merge` vs `+` (merge renumbers int keys; `+` keeps left's).
- Spread: `[...$a, ...$b]` (8.1 allows string keys). Destructure: `[$x, $y] = $arr`; `['id' => $id] = $row`.
- `in_array($n, $a, true)` — always pass strict `true` (loose finds `0 == 'abc'`).

## Composer / autoloading / PSR
- `composer.json` → `require`/`require-dev`; `composer install` (uses lock), `composer update` (re-resolves). `composer dump-autoload -o` for optimized classmap.
- PSR-4 autoload: map namespace prefix to dir: `"autoload": {"psr-4": {"App\\": "src/"}}`. Class `App\Service\Mailer` → `src/Service/Mailer.php`.
- Key PSRs: PSR-4 (autoload), PSR-12 (style), PSR-7 (HTTP messages), PSR-11 (container), PSR-3 (logger), PSR-15 (middleware).
- `use App\Foo;` imports; alias `use App\Foo as Bar;`. Leading `\` = fully-qualified from root.

## PDO + prepared statements (SQL — never interpolate)
```php
$stmt = $pdo->prepare('SELECT * FROM users WHERE email = :email');
$stmt->execute(['email' => $email]);
$rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
```
- Construct with error mode on: `new PDO($dsn, $u, $p, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_EMULATE_PREPARES => false])`. Emulated prepares can undermine typed binding — disable.
- Named `:x` or positional `?` placeholders. Placeholders bind **values only** — table/column names must be whitelisted, never bound.
- Transactions: `$pdo->beginTransaction(); ... $pdo->commit();` in try, `rollBack()` in catch.

## Errors & exceptions
- `Throwable` = `Error` (engine: `TypeError`, `\DivisionByZeroError`) + `Exception` (app). Catch `\Throwable` to catch both.
- Multi-catch: `catch (TypeError|ValueError $e)`. `finally` always runs. `throw` is an expression (8.0): `$x = $v ?? throw new \InvalidArgumentException();`.
- Suppress with `@` only for known-noisy calls; prefer `error_reporting(E_ALL)`. Convert warnings to exceptions via `set_error_handler`.

## Laravel essentials
- Eloquent ORM: `User::where('active', true)->get()`; `User::find($id)`; mass-assign guarded by `$fillable`/`$guarded`. **N+1**: use `User::with('posts')->get()` eager loading; detect with `Model::preventLazyLoading()`.
- Migrations: `Schema::create('users', fn(Blueprint $t) => ...)`; `php artisan migrate`. Facades (`DB::`, `Cache::`) are static proxies to container services. Service container + `app()->make()`; DI via constructor. Artisan, Blade templates, queues, Eloquent relationships (`hasMany`/`belongsTo`).

## Symfony essentials
- Components (HttpFoundation, Console, DependencyInjection) usable standalone. Bundles, autowired services via `services.yaml`, `#[Route]` attributes on controllers, Doctrine ORM (entities + `EntityManager`), Twig templates, `bin/console` commands.

## Traits, closures, generators
- Traits inject reusable methods (horizontal reuse — PHP has no multiple inheritance): `use LoggerTrait;` inside a class. Conflicts resolved with `insteadof`/`as`. Traits can hold abstract methods + static props.
- Closures capture by value with `use ($x)` (copy) or `use (&$x)` (reference): `fn($y) => $x + $y` (arrow fns auto-capture by value, one expression). `Closure::bind` rebinds `$this`.
- Generators `yield` values lazily (constant memory over huge sequences): `function gen() { foreach ($rows as $r) yield $r; }`. `yield $k => $v` for keys; `yield from $iter` delegates. Consumed once.
- `Iterator`/`IteratorAggregate`/`Countable`/`ArrayAccess` interfaces make objects behave like arrays in `foreach`/`count`/`$obj[$k]`.

## Strings & useful stdlib
- Interpolation in double quotes `"Hi $name"`/`"{$arr['k']}"`; single quotes literal. Heredoc `<<<EOT` interpolates, nowdoc `<<<'EOT'` doesn't.
- `sprintf`, `str_contains`/`str_starts_with`/`str_ends_with` (8.0), `explode`/`implode`, `trim`, `preg_match`/`preg_replace` (PCRE), `mb_*` for multibyte/UTF-8 (`strlen` counts bytes — use `mb_strlen`).
- `null` coalescing chains for arrays: `$data['a']['b'] ?? null` never warns on missing keys.

## Interfaces, abstract, visibility, static
- `interface I { public function f(): int; }` (contracts, multiple `implements`); `abstract class` (partial impl, can't instantiate). Constants in interfaces/enums `const MAX = 10;` accessed `self::MAX`/`Foo::MAX`.
- Visibility `public`/`protected`/`private`; `final` blocks override/extend. `static` methods/props on the class not instance; `Foo::bar()`. `__construct`/`__destruct`/`__toString`/`__get`/`__set`/`__invoke` magic methods.
- Generics don't exist at runtime — use PHPDoc `@param array<int, User>` + static analysis (PHPStan/Psalm) for type safety on collections.

## Testing & tooling
- PHPUnit: `class FooTest extends TestCase { public function testAdds(): void { $this->assertSame(3, add(1,2)); } }`. Data providers, mocks (`createMock`). Pest is a modern alt.
- PHPStan/Psalm static analysis (levels), PHP-CS-Fixer for PSR-12 style, Xdebug for debugging/coverage. `composer.json` `scripts` for task shortcuts.

## Gotchas -> Fix
- `==` loose compare: `0 == 'foo'` was true pre-8.0 (8.0 fixed to false), but `'1e2' == '100'` still true (numeric strings), `'0' == false` true -> always `===`.
- `array_filter` keeps original keys -> JSON turns list into object; wrap in `array_values(...)`.
- `array_map` with keys: doesn't get keys; use `foreach` or `array_map(fn($k,$v)=>..., array_keys($a), $a)`.
- Passing array to function mutates nothing (copy) -> use `&$arr` ref or return new array; but object props DO mutate.
- `foreach ($arr as &$v) {}` leaves `$v` dangling as reference to last element — next `foreach ($arr as $v)` corrupts array. `unset($v)` after the reference loop.
- `isset($a['k'])` is false when value is `null`; use `array_key_exists('k', $a)` to distinguish null-vs-missing.
- `empty()` true for `0`, `'0'`, `''`, `[]`, `null`, `false` — don't use to check "present"; use `isset`/`=== null`.
- Float compare `0.1 + 0.2 != 0.3` -> compare with epsilon or use bcmath/int cents.
- String-to-number: `(int)"12abc"` = 12 silently; `intval`, or `filter_var($s, FILTER_VALIDATE_INT)` for validation.
- `null` passed to non-nullable builtin param (`strlen(null)`) deprecated in 8.1 -> coalesce or type-guard.
- `static::` (late static binding) vs `self::` — `self` binds to defining class, `static` to called class; use `static` in factories.
- `require` a file returning array once; `include` warns on missing, `require` fatals. Use Composer autoload not manual requires.
- Timezone/`DateTime` mutability: `DateTime` is mutable (`->modify` changes in place); use `DateTimeImmutable` to avoid aliasing bugs.
- `json_encode` returns `false` on error (e.g. invalid UTF-8) — check or pass `JSON_THROW_ON_ERROR`.
- Integer overflow silently promotes to float (`PHP_INT_MAX + 1`) — no exception.
