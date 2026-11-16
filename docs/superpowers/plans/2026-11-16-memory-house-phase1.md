# «Дом памяти» — Этап 1 (ядро архива / MVP) — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Играбельное демо: игрок импортирует фото/текст/аудио/видео со сжатием и конвертацией, раскладывает воспоминания по темам в готовом домике на 4–5 комнат, ищет их, смотрит от первого лица; всё надёжно сохраняется, синхронизируется со Steam Cloud и экспортируется.

**Architecture:** Два C++-модуля. `MemoryCore` — логика без графики (модель данных, каталог SQLite, библиотека файлов, конвертация, импорт, поиск, экспорт, облако); покрыт автотестами UE Automation Spec. `MemoryHouse` — игра (дом, предметы-носители, камеры, UI), ссылается на воспоминания только по `FGuid`. Дом и архив сохраняются раздельно.

**Tech Stack:** Unreal Engine 5 (последняя стабильная на старте), C++ + Blueprints/UMG, SQLiteCore, ImageWrapper, Media Framework (Electra), RuntimeAudioImporter (MIT), Online Subsystem Steam / Steamworks SDK, конвертер по итогам Task 0.

**Spec:** `docs/superpowers/specs/2026-11-16-memory-house-design.md`

**Где выполняется:** локально на Windows с установленным UE5 и Claude Code, подключённым через `unreal-mcp`. Облачная сессия Claude Code этот план выполнить не может (нет редактора).

## Global Constraints

- Платформа: Windows; Steam Deck/macOS/Linux — не в этом этапе.
- Хранение: всё в `FPaths::ProjectSavedDir()/Archive/` (папка сохранений пользователя в сборке), никогда в папке установки. Оригинал игрока не изменяется и не удаляется.
- Сжатие «визуально без потерь»: фото — разрешение сохраняется, кроме > 8192 px по длинной стороне (уменьшить до 8192); перекодировать в JPEG качества 92; если исходный JPEG/PNG уже меньше результата — хранить исходные байты как есть.
- Видео: хранение H.264 + AAC в MP4, CRF 19, не выше 1080p; длительность ≤ 120 с; файл ≤ 100 МБ после сжатия. Длиннее — предложить обрезку, не отклонять.
- Аудио: ≤ 600 с; WAV → OGG Vorbis q6; MP3/OGG — как есть; M4A/AAC — как есть.
- Принимаемые форматы: фото JPEG/PNG/HEIC; видео MP4/MOV (H.264, HEVC); аудио MP3/M4A/OGG/WAV.
- Один файл в Steam Cloud ≤ 100 МБ; квота по умолчанию 1 ГБ (читать фактическую через API). При нехватке — воспоминание остаётся локальным с пометкой «не в облаке»; ничего не отклоняется и не удаляется.
- Любая запись на диск — атомарно (временный файл → переименование); каталог — в транзакции.
- Текст и имена файлов — Unicode (кириллица обязательна).
- Языки UI: английский + русский (String Tables).
- Без своих серверов; без сети в этом этапе.
- Приватность: шифрования нет.

## Review Focus

1. **Сбой посреди импорта** (вылет, выключение ПК): после перезапуска нет полузаписанных файлов и «битых» записей каталога; повторный импорт работает. → тест в Task 5.
2. **Файл не того формата / повреждённый / HEIC без кодека:** понятная ошибка, архив не меняется. → тест в Task 4 и Task 5.
3. **Тот же файл импортирован дважды:** одно хранилище байтов (дедупликация по хэшу), два воспоминания допустимы; удаление одного не ломает другое. → тест в Task 3.
4. **Кириллица, эмодзи и пробелы в путях и текстах:** импорт, поиск и экспорт работают. → тест в Task 6 и Task 7.
5. **Облако переполнено или Steam не запущен:** игра работает локально, пометка «не в облаке», без падений. → тест в Task 8.

---

## Структура файлов

```
MemoryHouse/                         (новый git-репозиторий игры)
  MemoryHouse.uproject
  Config/DefaultEngine.ini           Steam, Auto-Cloud не используем — см. Task 8
  Scripts/RunTests.ps1               запуск автотестов по фильтру
  Docs/                              копия spec + этот план
  Source/MemoryCore/
    MemoryCore.Build.cs
    Public/MemoryTypes.h             модель данных
    Public/ArchivePaths.h            пути архива
    Public/FileStore.h               библиотека файлов (хэш, атомарная запись)
    Public/MediaConverter.h          интерфейс конвертации + правила
    Public/ImportService.h           конвейер импорта, очередь
    Public/CatalogStore.h            SQLite-каталог, миграции
    Public/SearchService.h           поиск
    Public/ArchiveExporter.h         экспорт/импорт архива
    Public/CloudSync.h               Steam Cloud
    Private/...                      реализации
    Private/Tests/*.spec.cpp         автотесты (MemoryHouse.Core.*)
    Private/Tests/Fixtures/          тестовые файлы (см. Task 0)
  Source/MemoryHouse/
    House/                           дом, сохранение раскладки, размещение
    Carriers/                        предметы-носители
    Player/                          камеры и управление
    UI/                              C++-база виджетов
  Content/MemoryHouse/...            уровень, ассеты, виджеты UMG
```

Тесты запускаются так (`Scripts/RunTests.ps1 <Filter>`):

```powershell
& "$env:UE_ROOT\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "$PWD\MemoryHouse.uproject" `
  -ExecCmds="Automation RunTests $Filter; Quit" -unattended -nullrhi -nosound -nop4 -log
```
Успех: в логе `Test Completed. Result={Success}` для каждого теста и нет `Result={Fail}`; код выхода 0.

---

### Task 0: Спайк конвертации и проверка Steam (выбрасываемый)

**Files:**
- Create: `Docs/spike-conversion.md` (итог), `Source/MemoryCore/Private/Tests/Fixtures/` (тестовые медиа)

Цель — решение, а не код. Код спайка не сохраняется.

- [ ] **Step 1:** Собрать фикстуры: `photo_iphone.heic`, `photo_large_9000px.jpg`, `photo_small.jpg` (< 200 КБ), `photo_cyr_имя файла 😀.png`, `video_iphone_hevc_30s.mov`, `video_h264_150s.mp4`, `video_4k_20s.mp4`, `audio.wav`, `audio.mp3`, `audio.m4a`, `broken.jpg` (обрезанный файл), `fake.mp4` (текст с расширением .mp4). Только свои или CC0 материалы.
- [ ] **Step 2:** Путь (а) — Windows Media Foundation: декодировать HEVC MOV и HEIC, закодировать H.264 MP4 с CRF-эквивалентом. Записать, что работает без расширений Microsoft Store.
- [ ] **Step 3:** Путь (б) — ffmpeg LGPL-сборка (динамические DLL, без `--enable-gpl`, без libx264) с кодировщиком H.264 из Media Foundation (`h264_mf`) + libheif для HEIC. Проверить те же файлы.
- [ ] **Step 4:** Записать в `Docs/spike-conversion.md`: выбранный путь, список лицензий для экрана «Титры/лицензии», открытые вопросы для юриста (патенты HEVC/H.264), время конвертации 30-секундного 4K-ролика.
- [ ] **Step 5:** В Steamworks: включить Steam Cloud, выставить квоту (запросить > 1 ГБ, записать фактическую), лимит файлов. Записать в тот же документ.
- [ ] **Step 6:** Проверить, что `SQLiteCore` в текущей версии UE поддерживает FTS5 (`CREATE VIRTUAL TABLE t USING fts5(x)`). Записать результат — от него зависит Task 6.
- [ ] **Step 7: Commit** `docs: conversion and platform spike results`

---

### Task 1: Проект и модель данных

**Files:**
- Create: `MemoryHouse.uproject`, `Source/MemoryCore/MemoryCore.Build.cs`, `Source/MemoryCore/Public/MemoryTypes.h`, `Source/MemoryCore/Public/ArchivePaths.h`, `Scripts/RunTests.ps1`
- Test: `Source/MemoryCore/Private/Tests/MemoryTypes.spec.cpp`

**Interfaces:**
- Produces:
  - `enum class EAttachmentKind : uint8 { Photo, Text, Audio, Video };`
  - `enum class EDatePrecision : uint8 { Unknown, Year, Season, Month, Day };`
  - `struct FFuzzyDate { int32 Year=0; int32 Month=0; int32 Day=0; EDatePrecision Precision; FText ToDisplayString(const FString& CultureName) const; bool operator<(const FFuzzyDate&) const; }` — сезон кодируется `Month` = 1/4/7/10 + `Precision=Season`.
  - `struct FMemoryAttachment { FGuid Id; EAttachmentKind Kind; FString BlobHash; FString Text; int32 DurationMs=0; int32 Width=0; int32 Height=0; bool bLocalOnly=false; }`
  - `struct FMemoryRecord { FGuid Id; FString Title; FString Description; FFuzzyDate Date; FGuid ThemeId; TArray<FMemoryAttachment> Attachments; TArray<FString> People; FDateTime CreatedUtc; FDateTime ModifiedUtc; }`
  - `struct FMemoryTheme { FGuid Id; FString Name; FLinearColor Color; int32 SortOrder; }`
  - `namespace ArchivePaths { FString Root(); FString Blobs(); FString LocalOnlyBlobs(); FString CatalogDb(); FString HouseSave(); FString Staging(); }` — `Root()` = `ProjectSavedDir()/Archive`; `LocalOnlyBlobs()` вне облачного пути.
  - Все структуры — `USTRUCT(BlueprintType)`.

- [ ] **Step 1:** Создать пустой C++-проект UE5 `MemoryHouse` в новом git-репозитории; добавить модуль `MemoryCore` (Runtime); скопировать spec и этот план в `Docs/`; добавить `Scripts/RunTests.ps1`. Проверка: проект собирается, `RunTests.ps1 MemoryHouse.Core` завершается с кодом 0 (0 тестов).
- [ ] **Step 2: Тест** `MemoryHouse.Core.Types`:
  - `FFuzzyDate{2019,7,0,Season}.ToDisplayString("ru")` == `"лето 2019"`; `"en"` == `"Summer 2019"`.
  - сортировка: `{2019,0,0,Year}` < `{2019,7,0,Season}` < `{2019,8,12,Day}` < `{2020,0,0,Year}`; `Unknown` — в конце.
  - `ArchivePaths::Root()` заканчивается на `/Archive` и находится внутри `FPaths::ProjectSavedDir()`.
- [ ] **Step 3:** Запустить — FAIL (нет типов).
- [ ] **Step 4:** Реализовать `MemoryTypes.h`, `ArchivePaths.h`.
- [ ] **Step 5:** Запустить — PASS.
- [ ] **Step 6: Commit** `feat(core): project scaffold and memory data model`

---

### Task 2: Каталог (SQLite) с миграциями

**Files:**
- Create: `Public/CatalogStore.h`, `Private/CatalogStore.cpp`, `Private/CatalogSchema.cpp`
- Test: `Private/Tests/CatalogStore.spec.cpp`

**Interfaces:**
- Consumes: типы Task 1.
- Produces: `class FCatalogStore`:
  - `bool Open(const FString& DbPath, FText& OutError);` — создаёт/мигрирует схему; `PRAGMA journal_mode=WAL`.
  - `int32 GetSchemaVersion() const;` (текущая = 1)
  - `bool UpsertMemory(const FMemoryRecord&);` `TOptional<FMemoryRecord> GetMemory(const FGuid&) const;` `bool DeleteMemory(const FGuid&);`
  - `bool UpsertTheme(const FMemoryTheme&);` `TArray<FMemoryTheme> GetThemes() const;` `bool DeleteTheme(const FGuid&, const FGuid& MoveMemoriesTo);`
  - `TArray<FMemoryRecord> GetMemoriesByTheme(const FGuid&) const;`
  - `int32 CountBlobReferences(const FString& BlobHash) const;`
  - `bool RunInTransaction(TFunctionRef<bool()> Body);` — откат, если `Body` вернул false.

- [ ] **Step 1: Тесты** `MemoryHouse.Core.Catalog`:
  - открыть БД во временной папке → `GetSchemaVersion()==1`;
  - upsert memory с 3 вложениями, `Title="Лето у бабушки 😀"` → `GetMemory` возвращает равную запись (все поля, порядок вложений);
  - `DeleteTheme(A, B)` переносит воспоминания темы A в B;
  - `RunInTransaction` с `Body` вернувшим false → изменений нет;
  - закрыть и открыть заново → данные на месте.
- [ ] **Step 2:** Запустить — FAIL.
- [ ] **Step 3:** Реализовать. Таблицы: `themes`, `memories`, `attachments(memory_id, ord, ...)`, `people(memory_id, name)`, `meta(schema_version)`. Миграции — массив SQL-скриптов по версиям.
- [ ] **Step 4:** Запустить — PASS.
- [ ] **Step 5: Commit** `feat(core): sqlite catalog with migrations`

---

### Task 3: Библиотека файлов (FileStore)

**Files:**
- Create: `Public/FileStore.h`, `Private/FileStore.cpp`
- Test: `Private/Tests/FileStore.spec.cpp`

**Interfaces:**
- Consumes: `ArchivePaths`.
- Produces: `class FFileStore`:
  - `FString PutFile(const FString& SourcePath, const FString& Extension, bool bLocalOnly, FText& OutError);` — возвращает `BlobHash` (SHA-256 hex) + расширение, например `"ab12….jpg"`; пишет в `Staging/` → `rename` в `Blobs/ab/ab12….jpg` (или `LocalOnlyBlobs/`). Если blob уже есть — не пишет повторно.
  - `FString ResolvePath(const FString& BlobHash) const;` (ищет в обоих каталогах)
  - `bool MoveToLocalOnly(const FString& BlobHash);` `bool MoveToCloud(const FString& BlobHash);`
  - `bool DeleteBlob(const FString& BlobHash);`
  - `void CleanupStaging();` — удаляет всё в `Staging/` (вызывается при старте).
  - `int64 GetCloudBytesUsed() const;`

- [ ] **Step 1: Тесты** `MemoryHouse.Core.FileStore`:
  - `PutFile` одного и того же файла дважды → одинаковый хэш, на диске один файл (Review Focus 3);
  - путь источника с кириллицей и эмодзи работает;
  - после искусственного «сбоя» (файл оставлен в `Staging/`) `CleanupStaging()` его удаляет, `Blobs/` не тронут (Review Focus 1);
  - `MoveToLocalOnly` → `ResolvePath` указывает в `LocalOnlyBlobs/`, `GetCloudBytesUsed` уменьшился.
- [ ] **Step 2:** FAIL. **Step 3:** Реализовать (хэш — `FSHA256`/`FSHAHash` движка, потоково). **Step 4:** PASS.
- [ ] **Step 5: Commit** `feat(core): content-addressed file store with atomic writes`

---

### Task 4: Конвертация медиа

**Files:**
- Create: `Public/MediaConverter.h`, `Private/MediaConverter_<Path>.cpp` (путь из Task 0), `Private/MediaRules.cpp`
- Test: `Private/Tests/MediaConverter.spec.cpp`
- Modify: `MemoryCore.Build.cs` (зависимости/DLL конвертера, `RuntimeDependencies`)

**Interfaces:**
- Produces:
  - `struct FMediaProbe { EAttachmentKind Kind; FString Container; FString Codec; int32 Width=0, Height=0, DurationMs=0; int64 Bytes=0; bool bValid=false; FText Error; };`
  - `struct FConvertRequest { FString SourcePath; FString OutPath; double TrimStartSec=0; double TrimEndSec=0; };`
  - `class IMediaConverter { virtual FMediaProbe Probe(const FString& Path) = 0; virtual bool Convert(const FConvertRequest&, TFunction<void(float)> OnProgress, const FThreadSafeBool& bCancel, FText& OutError) = 0; };`
  - `namespace MediaRules { bool NeedsTrim(const FMediaProbe&); FString StoredExtension(EAttachmentKind, const FMediaProbe&); bool ShouldKeepOriginal(const FMediaProbe& In, int64 ConvertedBytes); FIntPoint TargetSize(const FMediaProbe&); }` — значения из Global Constraints.
  - `TSharedRef<IMediaConverter> CreateMediaConverter();`

- [ ] **Step 1: Тесты** `MemoryHouse.Core.Media` (на фикстурах Task 0):
  - `Probe(photo_iphone.heic)` → `Kind==Photo, bValid`; `Probe(fake.mp4)` и `Probe(broken.jpg)` → `!bValid`, `Error` не пустой (Review Focus 2);
  - `Convert(video_iphone_hevc_30s.mov)` → выход: MP4, H.264, ≤ 1080p, длительность 30 ± 0.2 с;
  - `video_4k_20s.mp4` → высота выхода 1080;
  - `MediaRules::NeedsTrim(video_h264_150s)` == true; с `TrimStart=10, TrimEnd=70` → выход 60 ± 0.2 с;
  - `photo_large_9000px.jpg` → длинная сторона 8192; `photo_small.jpg` → `ShouldKeepOriginal` true;
  - `audio.wav` → `.ogg`; `audio.mp3` → как есть;
  - установка `bCancel` во время конвертации → `Convert` возвращает false, выходной файл не создан.
- [ ] **Step 2:** FAIL. **Step 3:** Реализовать по выбранному пути. **Step 4:** PASS.
- [ ] **Step 5:** Добавить в `Docs/licenses.md` лицензии конвертера (для экрана титров).
- [ ] **Step 6: Commit** `feat(core): media probe and conversion`

---

### Task 5: Конвейер импорта с очередью

**Files:**
- Create: `Public/ImportService.h`, `Private/ImportService.cpp`
- Test: `Private/Tests/ImportService.spec.cpp`

**Interfaces:**
- Consumes: `FCatalogStore`, `FFileStore`, `IMediaConverter`, `MediaRules`.
- Produces: `UCLASS() class UImportService : public UGameInstanceSubsystem`:
  - `FGuid EnqueueImport(const FString& SourcePath, const FGuid& MemoryId, double TrimStartSec=0, double TrimEndSec=0);` — возвращает Id задания; добавляет вложение в существующее воспоминание.
  - `FMediaProbe ProbeFile(const FString& SourcePath);` — для UI до импорта (показать «нужно обрезать»).
  - `void Cancel(const FGuid& JobId);`
  - делегаты: `FOnImportProgress(FGuid JobId, float Progress)`, `FOnImportFinished(FGuid JobId, bool bOk, FText Error, FMemoryAttachment Attachment)`.
  - Выполнение — по одному заданию в фоновом потоке (`UE::Tasks`), результаты — на игровой поток.
  - Порядок: probe → проверка лимитов → convert в `Staging/` → `FileStore.PutFile` → `Catalog.RunInTransaction(добавить вложение)`. При ошибке на любом шаге — `Staging/` очищается, каталог не меняется.
  - Если `GetCloudBytesUsed()+размер > квота` (из `CloudSync`, Task 8; до Task 8 — заглушка `TFunction<int64()> GetCloudQuotaBytes`) → `bLocalOnly=true`.

- [ ] **Step 1: Тесты** `MemoryHouse.Core.Import`:
  - импорт `photo_iphone.heic` → `OnImportFinished(bOk)`; `GetMemory` содержит вложение `Photo` с `BlobHash`, файл по `ResolvePath` существует;
  - импорт `fake.mp4` → `bOk=false`, воспоминание без изменений, `Staging/` пуст (Review Focus 2);
  - симуляция сбоя: конвертер-заглушка бросает ошибку после записи в Staging → каталог без изменений; повторный импорт успешен (Review Focus 1);
  - 3 задания подряд → выполняются по очереди, прогресс монотонно растёт;
  - квота-заглушка = 0 → вложение `bLocalOnly=true`, файл в `LocalOnlyBlobs/` (Review Focus 5).
- [ ] **Step 2:** FAIL. **Step 3:** Реализовать. **Step 4:** PASS.
- [ ] **Step 5: Commit** `feat(core): background import pipeline`

---

### Task 6: Поиск

**Files:**
- Create: `Public/SearchService.h`, `Private/SearchService.cpp`; Modify: `CatalogSchema.cpp` (миграция 2: индекс)
- Test: `Private/Tests/Search.spec.cpp`

**Interfaces:**
- Consumes: `FCatalogStore`.
- Produces:
  - `struct FSearchQuery { FString Text; TOptional<FGuid> ThemeId; TOptional<FFuzzyDate> From; TOptional<FFuzzyDate> To; };`
  - `TArray<FGuid> FCatalogStore::Search(const FSearchQuery&) const;` — по `Title`, `Description`, `Attachments.Text`, `People`; без учёта регистра (включая кириллицу); результат по дате (новые сверху).
  - Реализация: FTS5, если Task 0 подтвердил; иначе отдельный столбец `search_text` в нижнем регистре (`FString::ToLower`, Unicode) + `LIKE`.

- [ ] **Step 1: Тесты** `MemoryHouse.Core.Search`:
  - запрос `"бабушк"` находит «Лето у Бабушки» (регистр, часть слова) (Review Focus 4);
  - фильтр по теме и диапазону дат `2019..2020` отсекает 2018;
  - надпись (вложение `Text`) находится по своему тексту;
  - пустой запрос + тема → все воспоминания темы.
- [ ] **Step 2:** FAIL. **Step 3:** Реализовать (миграция 2 строит индекс для существующих записей). **Step 4:** PASS.
- [ ] **Step 5: Commit** `feat(core): memory search`

---

### Task 7: Экспорт и импорт архива

**Files:**
- Create: `Public/ArchiveExporter.h`, `Private/ArchiveExporter.cpp`
- Test: `Private/Tests/ArchiveExporter.spec.cpp`

**Interfaces:**
- Consumes: `FCatalogStore`, `FFileStore`, `ArchivePaths::HouseSave()`.
- Produces:
  - `bool ExportArchive(const FString& DestFolder, TFunction<void(float)> OnProgress, FText& OutError);` — создаёт `DestFolder/MemoryHouse Export YYYY-MM-DD/`: `manifest.json` (схема 1, все темы и воспоминания), `memories.html` (читаемый список: тема → воспоминания → ссылки на файлы), `files/<Тема>/<дата> <заголовок>/<n>.<ext>` (имена очищены от недопустимых символов, кириллица сохраняется), `house.sav`.
  - `bool ImportArchive(const FString& ExportFolder, EImportMode Mode, FText& OutError);` — `enum class EImportMode { Merge, Replace }`; Merge пропускает воспоминания с уже существующим `Id`.

- [ ] **Step 1: Тесты** `MemoryHouse.Core.Export`:
  - экспорт 3 тем / 5 воспоминаний / 7 файлов → manifest содержит 5 записей, все файлы существуют, `memories.html` открывается как валидный HTML;
  - заголовок `Лето: "дача" / 2019?` → имя папки без `:"/?`, кириллица на месте (Review Focus 4);
  - экспорт → новый пустой архив → `ImportArchive(Merge)` → каталог эквивалентен исходному, хэши файлов совпадают;
  - повторный `Merge` того же экспорта не создаёт дублей.
- [ ] **Step 2:** FAIL. **Step 3:** Реализовать. **Step 4:** PASS.
- [ ] **Step 5: Commit** `feat(core): archive export and import`

---

### Task 8: Steam Cloud

**Files:**
- Create: `Public/CloudSync.h`, `Private/CloudSync.cpp`; Modify: `Config/DefaultEngine.ini` (OnlineSubsystemSteam, AppId), `MemoryCore.Build.cs` (Steamworks)
- Test: `Private/Tests/CloudSync.spec.cpp`

**Interfaces:**
- Consumes: `FFileStore`, `FCatalogStore`, `ArchivePaths`.
- Produces: `UCLASS() class UCloudSync : public UGameInstanceSubsystem`:
  - `bool IsAvailable() const;` — Steam запущен и Cloud включён у игрока.
  - `int64 GetQuotaBytes() const; int64 GetUsedBytes() const;` — `ISteamRemoteStorage::GetQuota`; если недоступно — `GetQuotaBytes()` = 0.
  - `void SyncUp();` `void SyncDown();` — файлы из `Blobs/`, `catalog.db` (снимок через `VACUUM INTO` во временный файл), `house.sav` через `ISteamRemoteStorage::FileWrite`/`FileRead`; каждый файл ≤ 100 МБ; сравнение по хэшу/метке времени.
  - делегат `FOnCloudStateChanged(ECloudState)`; `enum class ECloudState { Synced, Syncing, LocalOnly, Unavailable, QuotaFull };`
  - Абстракция `ICloudBackend` (Steam / заглушка в тестах).
- Решение: Steam Auto-Cloud не используем — нужен контроль квоты и пометок `bLocalOnly`.

- [ ] **Step 1: Тесты** `MemoryHouse.Core.Cloud` (заглушка `ICloudBackend`):
  - backend недоступен → `ECloudState::Unavailable`, импорт работает, все вложения `bLocalOnly` не меняются (Review Focus 5);
  - квота 10 МБ, файлов на 12 МБ → `SyncUp` выгружает влезающие, остальные помечаются `bLocalOnly` и переезжают в `LocalOnlyBlobs/`, состояние `QuotaFull`;
  - освобождение места → `MoveToCloud` и выгрузка при следующем `SyncUp`;
  - `SyncDown` на «новом ПК» (пустой архив) восстанавливает каталог и файлы.
- [ ] **Step 2:** FAIL. **Step 3:** Реализовать. **Step 4:** PASS.
- [ ] **Step 5:** Ручная проверка на двух ПК (или переустановке): импорт → выход → удалить локальный архив → запуск → всё на месте.
- [ ] **Step 6: Commit** `feat(core): steam cloud sync with quota handling`

---

### Task 9: Загрузка медиа в мир

**Files:**
- Create: `Source/MemoryHouse/Carriers/MediaLoader.h/.cpp`
- Modify: `MemoryHouse.Build.cs` (ImageWrapper, MediaAssets, RuntimeAudioImporter)
- Test: `Source/MemoryHouse/Private/Tests/MediaLoader.spec.cpp`

**Interfaces:**
- Consumes: `FFileStore::ResolvePath`.
- Produces: `UCLASS() class UMediaLoader : public UGameInstanceSubsystem`:
  - `void LoadPhotoAsync(const FString& BlobHash, int32 MaxSize, TFunction<void(UTexture2D*)> Done);` — кэш по `(BlobHash, MaxSize)`, мипы; превью 512 для дальних предметов, полный размер — при осмотре.
  - `void LoadAudioAsync(const FString& BlobHash, TFunction<void(USoundWave*)> Done);`
  - `UMediaPlayer* OpenVideo(const FString& BlobHash);` — `UFileMediaSource`.
  - `void Trim(int64 MaxBytes);` — LRU-выгрузка текстур.

- [ ] **Step 1: Тесты** `MemoryHouse.Game.MediaLoader`: фото из фикстуры → текстура нужного размера; повторный запрос — тот же объект из кэша; аудио → `USoundWave` с длительностью ± 0.1 с.
- [ ] **Step 2:** FAIL. **Step 3:** Реализовать. **Step 4:** PASS.
- [ ] **Step 5:** Ручная проверка видео: сконвертированный ролик проигрывается на плоскости в редакторе (через `unreal-mcp` или PIE).
- [ ] **Step 6: Commit** `feat(game): runtime media loading`

---

### Task 10: Дом, размещение и сохранение раскладки

**Files:**
- Create: `Source/MemoryHouse/House/HouseLayout.h/.cpp`, `House/PlacementComponent.h/.cpp`, `House/RoomVolume.h/.cpp`, `Content/MemoryHouse/Maps/StarterHouse.umap`
- Test: `Source/MemoryHouse/Private/Tests/HouseLayout.spec.cpp`

**Interfaces:**
- Consumes: `ArchivePaths::HouseSave()`.
- Produces:
  - `struct FPlacedItem { FGuid Id; FName CatalogItemId; FTransform Transform; FGuid MemoryId; FGuid RoomId; bool bIsReference=false; };` — `bIsReference` = явная «отсылка» на воспоминание, уже стоящее в другой комнате.
  - `struct FRoomInfo { FGuid RoomId; FGuid ThemeId; FText DisplayName; };`
  - `UCLASS() class UHouseLayoutSave : public USaveGame { int32 Version=1; TArray<FPlacedItem> Items; TArray<FRoomInfo> Rooms; }` — запись атомарно.
  - `ARoomVolume` (уровень): `FGuid RoomId`.
  - `UPlacementComponent`: привязка к сетке 10 см и поворот 15° на полу; на стенах — к поверхности стены; `bool CanPlace(const FTransform&) const` (без пересечений); `void PlaceItem(FName CatalogItemId)`, `void MoveItem(FGuid)`, `void RemoveItem(FGuid)`.
  - `UMemoryHouseItemCatalog` (DataAsset): список мебели/носителей `FName → {Mesh, Category, bIsCarrier, AllowedSurface}`.
  - Правило: одно воспоминание — один не-`bIsReference` предмет; попытка поставить второй → UI спрашивает «поставить отсылку?».

- [ ] **Step 1:** Уровень `StarterHouse`: 5 комнат, `ARoomVolume` в каждой, тёплое освещение, ассеты из 1–2 бесплатных stylized-паков (записать какие в `Docs/assets.md` с лицензиями).
- [ ] **Step 2: Тесты** `MemoryHouse.Game.Layout`: сохранение/загрузка раскладки идентичны; `Version` записан; повреждённый файл раскладки → загружается пустая раскладка + резервная копия `house.sav.bak` сохраняется; второй не-reference предмет для того же `MemoryId` запрещён.
- [ ] **Step 3:** FAIL. **Step 4:** Реализовать. **Step 5:** PASS.
- [ ] **Step 6:** Ручная проверка (PIE): поставить, сдвинуть, повернуть, удалить предмет; выйти, зайти — раскладка на месте.
- [ ] **Step 7: Commit** `feat(game): starter house, placement and layout save`

---

### Task 11: Камеры и управление

**Files:**
- Create: `Source/MemoryHouse/Player/MemoryPlayerController.h/.cpp`, `Player/BuildCameraPawn.h/.cpp`, `Player/WalkCharacter.h/.cpp`; Enhanced Input assets.

**Interfaces:**
- Produces: `AMemoryPlayerController`:
  - `enum class EViewMode { Build, Walk };` `void SetViewMode(EViewMode)` — плавный переход (≤ 1 с) между видом сверху и от первого лица; `Tab` — переключение.
  - `void FocusOnItem(FGuid PlacedItemId)` — в Build: камера летит к предмету; в Walk: персонаж телепортируется к предмету и смотрит на него.
  - Build: панорама/зум/вращение, срез этажа/стен («кукольный домик»). Walk: WASD + мышь, взаимодействие `E`/ЛКМ с носителем.

- [ ] **Step 1:** Реализовать. **Step 2:** Ручная проверка (PIE): переключение туда-обратно 10 раз без рывков; `FocusOnItem` в обоих режимах; геймпад работает (на будущее для Deck).
- [ ] **Step 3: Commit** `feat(game): build and walk camera modes`

---

### Task 12: Предметы-носители и их реакции

**Files:**
- Create: `Source/MemoryHouse/Carriers/MemoryCarrier.h/.cpp` (база), Blueprint-наследники `BP_PhotoFrame`, `BP_CorkBoard`, `BP_Album`, `BP_Note`, `BP_WallText`, `BP_TapeRecorder`, `BP_OldTV`.

**Interfaces:**
- Consumes: `UMediaLoader`, `FCatalogStore::GetMemory`, `FPlacedItem`.
- Produces: `AMemoryCarrier`:
  - `void BindMemory(const FGuid& MemoryId);` `UFUNCTION(BlueprintImplementableEvent) void OnMemoryBound(const FMemoryRecord&);`
  - `UFUNCTION(BlueprintImplementableEvent) void OnInspect();` / `OnStopInspect();` — видимая реакция (spec, риск «немой ролик»): фото «проявляется», записка раскрывается, катушки магнитофона крутятся, телевизор загорается.
  - `TArray<EAttachmentKind> SupportedKinds` — какие вложения носитель показывает.
- `BP_WallText`: текст надписи, 1 из 5 шрифтов (рукописный обязателен; все с кириллицей; лицензии в `Docs/licenses.md`), цвет, размер.

- [ ] **Step 1:** Реализовать базу и 7 носителей. **Step 2:** Ручная проверка (PIE): каждый носитель с реальным воспоминанием — реакция видна в беззвучной записи экрана за ≤ 3 с.
- [ ] **Step 3: Commit** `feat(game): memory carriers with inspect reactions`

---

### Task 13: Интерфейс

**Files:**
- Create: `Source/MemoryHouse/UI/*.h/.cpp` (C++-база), `Content/MemoryHouse/UI/WBP_*`, `Content/MemoryHouse/Localization/ST_UI` (en, ru).

Экраны и что каждый вызывает:
- **Добавить воспоминание:** выбор файлов (диалог Windows, мультивыбор) + перетаскивание файлов в окно игры → `ProbeFile`; если `NeedsTrim` — экран обрезки (два ползунка, превью, лимит 2:00) → `EnqueueImport`. Поля: заголовок, описание, дата (`FFuzzyDate`, выбор точности), тема, люди.
- **Очередь импорта:** прогресс по заданиям, отмена, понятные ошибки (текст ошибки из `FText Error`).
- **Темы:** создать/переименовать/цвет/удалить (с переносом), назначить комнате.
- **Поиск:** строка + фильтры темы и дат → список с превью → «Показать в доме» (`FocusOnItem`); воспоминания без предмета — «Поставить в дом».
- **Каталог мебели** в режиме Build.
- **Надпись:** создать/редактировать `BP_WallText` — текст, шрифт, цвет, размер; текст сохраняется как вложение `Text` воспоминания (ищется поиском).
- **Облако:** индикатор `ECloudState` + занято/квота; у воспоминаний `bLocalOnly` — значок «не в облаке» и подсказка про экспорт; напоминание об экспорте раз в 7 дней, если есть `bLocalOnly`.
- **Настройки:** язык, экспорт/импорт архива, титры и лицензии.
- **Первый запуск:** короткий онбординг: «добавь первое воспоминание» → предмет сразу появляется в первой комнате.

- [ ] **Step 1:** Реализовать экраны. **Step 2:** Ручной сценарий (PIE, оба языка): первый запуск → импорт HEIC + HEVC-видео (с обрезкой) + голос → три предмета в комнате → поиск по слову → «Показать в доме» → переключить язык → экспорт.
- [ ] **Step 3: Commit** `feat(game): archive UI`

---

### Task 14: Сборка демо и плейтест

**Files:**
- Create: `Docs/playtest.md` (сценарий и метрики), конфиги упаковки.

- [ ] **Step 1:** Упаковать Shipping-сборку Windows; проверить, что архив пишется в `%LOCALAPPDATA%/MemoryHouse/Saved/Archive`, а не рядом с exe.
- [ ] **Step 2:** Переустановка: удалить игру → установить → архив на месте.
- [ ] **Step 3:** Чистый Windows без кодеков из Store: импорт HEIC и HEVC работает (результат Task 0).
- [ ] **Step 4:** Плейтест 10–20 человек на основном App ID (ветка Steam `playtest`). Собрать метрики из отчёта оценки: доля добавивших ≥ 5 воспоминаний за первую сессию (порог ≥ 50 %), доля вернувшихся в течение недели (порог ≥ 33 %). Записать в `Docs/playtest.md`.
- [ ] **Step 5: Commit** `chore: phase 1 demo build and playtest notes`
