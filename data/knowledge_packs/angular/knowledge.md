# Angular (standalone, signals, RxJS)

## Standalone components (current default, v17+)
```ts
@Component({
  selector: 'app-user', standalone: true, // standalone is default in v19+
  imports: [CommonModule, RouterLink, ChildComp], // deps imported directly
  template: `<h1>{{name()}}</h1>`,
})
export class UserComponent {
  name = signal('Ada');
}
```
- No `NgModule` needed. `bootstrapApplication(AppComponent, { providers: [...] })` in `main.ts`. Legacy: `@NgModule({declarations,imports,providers})` still works; `imports` needs `RouterModule`, `FormsModule`, etc.

## Signals (v16+, reactivity)
- `const c = signal(0)` — read `c()`, write `c.set(1)` / `c.update(n => n+1)`. Objects: `c.update(o => ({...o, k:v}))` (replace, don't mutate for change detect).
- `const d = computed(() => c() * 2)` — lazy, memoized, read `d()`; deps auto-tracked; must be pure.
- `effect(() => { console.log(c()) })` — runs on dep change; in injection context (constructor/field init) or pass `{injector}`; auto-cleanup on destroy; `onCleanup` arg for teardown.
- `input()` / `input.required<T>()` — signal inputs (replaces `@Input`): `id = input(0)`, `id = input.required<number>()`; read `this.id()`. Transform: `input(0, {transform: numberAttribute})`.
- `output()` — `saved = output<number>()`; emit `this.saved.emit(1)` (replaces `@Output` EventEmitter).
- `model()` — two-way signal: `value = model('')` <-> `<app-x [(value)]="v"/>`.
- `viewChild`/`viewChildren`/`contentChild` signal queries. `linkedSignal` (writable derived), `resource()`/`rxResource` (async, experimental->stabilizing).
- Interop: `toSignal(obs$)` / `toObservable(sig)` from `@angular/core/rxjs-interop`.

## RxJS / Observables
- Observables = lazy push streams; subscribe to run. Operators via `.pipe(map, filter, switchMap, debounceTime, catchError, takeUntil, ...)`.
- Flattening: `switchMap` (cancel prev — typeahead/routing), `mergeMap` (concurrent), `concatMap` (queue/order), `exhaustMap` (ignore while busy — save buttons).
- `Subject`/`BehaviorSubject(seed)`/`ReplaySubject` for multicast state. `combineLatest`, `forkJoin` (parallel, completes), `startWith`, `shareReplay(1)` (cache).
- Unsubscribe: `takeUntilDestroyed()` (rxjs-interop, auto), `async` pipe (auto un/subscribe), or manual `Subscription`.

## Dependency Injection
- `constructor(private http: HttpClient) {}` OR `private http = inject(HttpClient)` (field, preferred in standalone). `inject()` only in injection context.
- `@Injectable({providedIn: 'root'})` = app-wide singleton, tree-shakable. Provide at component level via `providers:[Svc]` = new instance per component subtree.
- Provider forms: `{provide: TOKEN, useClass}`, `useValue`, `useFactory: () => ..., deps:[]`, `useExisting`. `InjectionToken<T>('desc')` for non-class deps. `@Optional`, `@Self`, `@SkipSelf`, `@Host` modify resolution.
- Hierarchical injectors: request bubbles up from element -> component -> module/root; first provider wins. Root providers = shared; component providers = isolated.

## Change detection
- Default (Zone.js): CD runs on any async event (click, timer, XHR) patched by zone.js, checking the whole tree top-down.
- `ChangeDetectionStrategy.OnPush`: component re-checks only when an `@Input`/signal ref changes, an event fires in it, an `async` pipe emits, or `markForCheck()` is called. Big perf win; requires immutable inputs.
- `ChangeDetectorRef`: `markForCheck()`, `detectChanges()`, `detach()/reattach()`. `NgZone.runOutsideAngular()` to skip CD for hot loops.
- Signals enable fine-grained/zoneless CD; `provideZonelessChangeDetection()` (v18+ experimental->stable) removes zone.js — then signals/async pipe drive updates.

## Templates / directives / pipes
- Control flow (v17+): `@if (x) {} @else {}`, `@for (i of list; track i.id) {} @empty {}`, `@switch (v) { @case('a'){} @default{} }`, `@defer (on viewport) {} @placeholder {} @loading {}`. Track is required in `@for`.
- Legacy structural: `*ngIf`, `*ngFor="let i of list; trackBy: fn"`, `*ngSwitch`. Attribute: `[ngClass]`, `[ngStyle]`.
- Binding: `[prop]="x"` property, `(event)="f($event)"`, `[(ngModel)]="x"` banana-in-box two-way (needs `FormsModule`). `#ref` template ref var.
- Custom directive `@Directive({selector:'[appHi]'})`; `@HostBinding`/`@HostListener` or `host:{}`.
- Pipes: `{{ d | date:'short' }}`, `| async`, `| json`, `| currency`, `| number`. Pure by default (memoized by ref); `pure:false` re-runs each CD. `@Pipe({name})` + `transform()`.

## Forms
- Reactive (preferred): `import ReactiveFormsModule`. `fb = inject(FormBuilder); form = fb.group({email:['', [Validators.required, Validators.email]], pw:['']})`. Template `[formGroup]="form"` + `formControlName="email"`. Read `form.value`, `form.get('email')?.errors`, `form.valid`, `form.controls`. `FormArray` for dynamic lists. `valueChanges`/`statusChanges` are Observables.
- Template-driven: `import FormsModule`; `[(ngModel)]` + `#f="ngForm"` + `required`/`email` attrs; simpler, less scalable.

## Routing
- `provideRouter(routes)` + `<router-outlet/>`. `routes = [{path:'users/:id', component:UserC, canActivate:[authGuard], resolve:{user:userResolver}, children:[...], loadComponent:()=>import('./x').then(m=>m.X)}]`.
- Nav: `<a routerLink="/users" routerLinkActive="active">`, `router.navigate(['/users', id])`. `route = inject(ActivatedRoute)`: `route.paramMap`/`snapshot.paramMap.get('id')`, `route.data`. Signal inputs from route via `withComponentInputBinding()`.
- Functional guards (v15+): `const authGuard: CanActivateFn = (route,state) => inject(Auth).ok() ? true : inject(Router).createUrlTree(['/login'])`. Resolvers: `ResolveFn<T>` prefetch data before activation. `lazy loadChildren`.

## HttpClient + interceptors
- `provideHttpClient(withInterceptors([authInterceptor]))`. `http.get<T>(url, {params})` returns cold Observable (subscribe or `async` pipe to fire). `firstValueFrom(obs$)` for promise.
- Functional interceptor: `const authInterceptor: HttpInterceptorFn = (req, next) => next(req.clone({setHeaders:{Authorization:tok}}))`. Chain for auth, logging, retry, error handling.

## Lifecycle hooks
- `ngOnInit` (after first inputs set — do init/fetch here, not constructor), `ngOnChanges(changes)` (on `@Input` change — decorator inputs only, not signal inputs), `ngAfterViewInit` (view/`@ViewChild` ready), `ngAfterContentInit` (projected content), `ngOnDestroy` (cleanup). `afterNextRender`/`afterRender` (v17+) for DOM-safe/SSR-skipped work.

## Content projection + templates
- `<ng-content select=".header"></ng-content>` projects children (multi-slot via `select`). `<ng-container>` = logical group, no DOM. `<ng-template>` = lazy template; render via `*ngIf="x; else tpl"` / `ngTemplateOutlet`; `TemplateRef` + `ViewContainerRef.createEmbeddedView` for dynamic.
- `@ViewChild(Cmp) child!: Cmp` / signal `viewChild(Cmp)`; `@ContentChild` for projected. `ElementRef`/`Renderer2` for DOM (SSR-safe writes).

## SSR / hydration / build
- `provideClientHydration()` + `@angular/ssr` for server render + non-destructive hydration (reuses server DOM). `@defer` for lazy hydration/loading. Standalone + `bootstrapApplication` on server. Angular CLI uses esbuild/Vite; `ng build`, `ng serve`, `ng generate`.

## Testing (brief)
- `TestBed.configureTestingModule({imports:[Cmp], providers:[{provide:Svc,useValue:mock}]})`; `fixture.detectChanges()`; `fixture.nativeElement`; `HttpTestingController` for HTTP; `fakeAsync`/`tick` for timers.

## Gotchas -> Fix
- Subscription leaks (manual `.subscribe` never torn down) -> `takeUntilDestroyed()`, `async` pipe, or store + `unsubscribe()` in `ngOnDestroy`.
- OnPush view not updating after mutating an object/array in place -> replace reference (`arr = [...arr]`) or use signals; `markForCheck()` if from outside.
- `ExpressionChangedAfterItHasBeenCheckedError` -> value changed after CD in same tick (usually in `ngAfterViewInit`/child->parent). -> move to `ngOnInit`, `setTimeout`, or signals.
- `nested switchMap` cancels in-flight save you wanted to keep -> use `exhaustMap` (ignore during) or `concatMap` (queue) for mutations, `switchMap` only for cancelable reads.
- `inject()` throws "outside injection context" -> call only in constructor/field initializers or pass an `injector`; wrap with `runInInjectionContext`.
- DI "No provider for X" -> not `providedIn:'root'` and not in `providers`; or provided in a sibling injector, not an ancestor. Check hierarchy.
- Component-level `providers:[Svc]` unexpectedly gives separate instances per component -> move to `providedIn:'root'` for a shared singleton.
- HttpClient call "does nothing" -> Observable is cold; nobody subscribed. -> `async` pipe, `.subscribe()`, or `firstValueFrom`.
- `@for` compile error -> `track` expression is required; use a unique id, not `$index` if items reorder.
- Zone.js not detecting change from a 3rd-party callback outside Angular -> `ngZone.run(() => ...)` to re-enter, or use signals + zoneless.
- Two-way `[(ngModel)]` errors -> import `FormsModule`; reactive forms need `ReactiveFormsModule` instead.
- `effect()` used to set signals -> can loop / is discouraged; use `computed`/`linkedSignal` for derived state, effects only for side effects (DOM, logging).
- Standalone component "not a known element" -> add it to the consumer's `imports` array (or its Directive/Pipe).
- `ngOnChanges` never fires for a signal input -> lifecycle `ngOnChanges` only tracks decorator `@Input`; for `input()` react with `computed`/`effect`.
- Fetching in the constructor -> inputs not yet bound; do it in `ngOnInit` (or with signal inputs + `computed`).
- Reading `@ViewChild` in `ngOnInit` returns undefined -> view not built yet; use `ngAfterViewInit` or `{static:false}`/signal `viewChild`.
- Pure pipe not updating after in-place array mutation -> pure pipes memoize by reference; replace the array or use `pipe:false` (perf cost).
- `async` pipe subscribes multiple times (used in several bindings) -> assign once via `*ngIf="obs$ | async as v"` and reuse `v`.
- Manual DOM via `document`/`ElementRef.nativeElement` breaks SSR -> use `Renderer2`, `afterNextRender`, or guard with `isPlatformBrowser`.
- `HttpClient` request fires twice -> two subscriptions (e.g. `async` pipe + manual); share with `shareReplay(1)` or subscribe once.
