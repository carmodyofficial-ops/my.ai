# MetaDatAdapter and MetaGlassesHost are referenced ONLY reflectively
# (Class.forName in GlassesHost.kt), so R8 sees no reachable reference and
# strips them. Both lookups are wrapped in runCatching { … }.getOrElse { Mock… },
# so a stripped class does not crash — it silently falls back to the MOCK
# adapter. A minified -PmetaSdk=true build would therefore ship an APK that
# pretends to talk to glasses it never opens a session with.
-keep class ai.my.glasses.wearables.MetaGlassesHost { *; }
-keep class ai.my.glasses.wearables.MetaDatAdapter { *; }
