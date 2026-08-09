Hermes Video Automation Architecture & Workflow

> Historical provenance authority. The active product is ILAIOS and the active capability is ILAIOS Video Automation / Video Factory. Historical Hermes naming below records the accepted source architecture; it does not define a separate active product.
# 1. Purpose and System Definition
Hermes Video Automation, Hermes platformu üzerinde çalışan; fikir aşamasından başlayarak video içeriğinin araştırılması, senaryolaştırılması, sahne planına dönüştürülmesi, medya varlıklarının üretilmesi veya temin edilmesi, seslendirilmesi, kurgulanması, altyazılanması, render edilmesi, doğrulanması ve sosyal medya platformlarında yayınlanmasına kadar olan süreci otomatikleştiren bağımsız bir üretim sistemidir.
Bu sistemin amacı yalnızca tek bir video oluşturmak değildir. Hermes Video Automation, sürekli ve tekrar kullanılabilir bir içerik üretim altyapısı olarak tasarlanacaktır.
Sistem:
Tek seferlik video üretimi
Seri video üretimi
Günlük içerik üretimi
Short-form video üretimi
Uzun format video üretimi
Platforma özel versiyon üretimi
Otomatik render
Otomatik kalite kontrol
Zamanlanmış yayınlama
Çoklu sosyal medya dağıtımı
işlevlerini destekleyecek şekilde kurulacaktır.
Hermes Video Automation hiçbir zaman belirli bir AI video üretim servisine, belirli bir sosyal medya platformuna veya tek bir medya üretim sağlayıcısına bağımlı olmayacaktır.

## 1.1 Core Architectural Principle
Hermes Video Automation'ın temel mimari prensibi:
Provider-independent orchestration
olacaktır.
Hermes doğrudan:
Seedance
Veo
Runway
Kling
herhangi bir TTS servisi
herhangi bir image generation servisi
YouTube
TikTok
Instagram
Facebook
için özel olarak tasarlanmayacaktır.
Bunun yerine Hermes genel interface ve provider katmanlarını kullanacaktır.
Örnek:
VideoGenerationProvider
Bu interface altında ileride:
SeedanceProvider
VeoProvider
RunwayProvider
KlingProvider
LocalTestVideoProvider
gibi implementasyonlar bulunabilir.
Hermes pipeline yalnızca şunu bilir:
generate_video(request)
Hangi servisin kullanılacağı configuration ve provider selection mekanizması tarafından belirlenir.
Bu prensip sayesinde herhangi bir servis:
pahalı hale gelirse,
kapanırsa,
API değiştirirse,
kalite kaybederse,
kullanım limiti getirirse,
daha iyi alternatif çıkarsa
Hermes'in ana video pipeline'ı yeniden yazılmadan provider değiştirilebilir.

## 1.2 Development and Production Separation
Video otomasyonu iki açık çalışma moduna sahip olacaktır.
TEST MODE
Amaç:
Pipeline'ın ücretsiz veya minimum maliyetle geliştirilmesi ve doğrulanmasıdır.
TEST MODE sırasında ücretli generative-video servislerinin çağrılması zorunlu olmayacaktır.
Kullanılabilecek kaynaklar:
Local test MP4 files
Static images
Generated placeholder assets
Local audio files
Free or local TTS
Synthetic metadata
Mock provider implementations
Örneğin:
LocalTestVideoProvider
önceden hazırlanmış test MP4 dosyalarını gerçek AI video sağlayıcısı gibi sisteme verir.
Hermes böylece:
scene planning,
asset resolution,
editing,
captioning,
render,
validation,
publishing preparation
işlemlerinin tamamını gerçek üretim maliyeti oluşturmadan test edebilir.
PRODUCTION MODE
Gerçek içerik üretiminde production provider'lar etkinleştirilir.
Örnek:
SeedanceProvider
veya gelecekte başka bir video provider.
Hermes'in kalan pipeline'ı TEST MODE ile aynı kalır.
Bu ayrım zorunludur.
Development sırasında gereksiz API maliyeti oluşturulmamalıdır.

## 1.3 End-to-End Canonical Workflow
Hermes Video Automation'ın ana işlem zinciri:
Input / Topic
↓
Research
↓
Content Planning
↓
Script Generation
↓
Scene Planning
↓
Shot Planning
↓
Asset Planning
↓
Media Generation / Acquisition
↓
Voice Generation
↓
Audio Processing
↓
Timeline Construction
↓
Video Editing / Assembly
↓
Music / SFX Integration
↓
Caption / Subtitle Generation
↓
Render
↓
Technical Validation
↓
Content Validation
↓
Approval / Publishing Decision
↓
Platform Adaptation
↓
Publishing
↓
Scheduling
↓
Post-Publish Verification
↓
Audit / Evidence / Metrics
Bu akış kanonik sıralamadır.
Modüller gerektiğinde bazı görevleri paralel yürütebilir; ancak dependency ilişkileri ihlal edilemez.
Örneğin final render işlemi, gerekli scene asset'leri hazır olmadan başlayamaz.

## 1.4 Input Layer
Her video işlemi bir VideoJob ile başlar.
VideoJob en az aşağıdaki bilgileri taşımalıdır:
job_id
project_id
topic
objective
target audience
target platforms
language
desired duration
video format
aspect ratio
content style
publishing strategy
provider policy
budget policy
approval policy
creation timestamp
VideoJob immutable kimliğe sahip olmalıdır.
Job oluşturulduktan sonra üretim sürecindeki tüm olaylar aynı job_id üzerinden izlenmelidir.

## 1.5 Research Layer
Research aşaması video senaryosu için gerekli bilgilerin toplanmasından sorumludur.
Bu aşamanın amacı rastgele içerik üretmek değildir.
Research output yapılandırılmış olmalıdır.
Örnek çıktı:
ResearchPacket
İçeriği:
topic summary
verified facts
source references
key claims
useful statistics
relevant dates
entities
risks
prohibited or uncertain claims
Research sonucunda yeterli güven seviyesine ulaşılamazsa script generation aşaması otomatik başlamamalıdır.

## 1.6 Script Generation Layer
Script Generator, ResearchPacket ve VideoJob bilgilerini kullanarak video metnini oluşturur.
Script yapısal olmalıdır.
Örnek:
VideoScript
hook
introduction
sections
narration
on-screen text
CTA
ending
estimated duration
Script yalnızca düz metin olarak saklanmamalıdır.
Her bölümün benzersiz bir kimliği olmalıdır.
Bu kimlikler ileride Scene Planner tarafından kullanılacaktır.

## 1.7 Scene and Shot Planning
VideoScript doğrudan AI video provider'a gönderilmeyecektir.
Önce iki aşamaya bölünür:
Scene Planner
Script'i mantıksal sahnelere ayırır.
Her Scene:
scene_id
script_reference
purpose
duration
visual description
narration reference
transition intent
required assets
bilgilerini içerir.
Shot Planner
Scene içerisindeki gerçek görsel çekimleri tanımlar.
Her Shot:
shot_id
scene_id
shot type
camera description
subject
action
environment
framing
movement
estimated duration
generation prompt
required provider capability
bilgilerini taşır.
Bu ayrım önemlidir.
Scene içerik mantığını temsil eder.
Shot gerçek video/görsel üretim birimidir.

## 1.8 Asset Planning
Her shot için gereken medya türü önceden belirlenir.
Örnek asset türleri:
AI video
stock video
image
generated image
screen recording
logo
graphic
icon
chart
voice track
music
sound effect
subtitle
overlay
Asset Planner doğrudan üretim yapmaz.
Sadece neye ihtiyaç olduğunu tanımlar.
Her asset:
AssetRequest
olarak temsil edilir.

## 1.9 Media Provider Architecture
Medya üretim sistemi provider abstraction kullanacaktır.
Temel provider sınıfları:
VideoGenerationProvider
AI veya diğer yöntemlerle video üretir.
ImageGenerationProvider
Görsel üretir.
StockMediaProvider
Var olan medya kütüphanelerinden asset getirir.
VoiceProvider
TTS veya voice generation gerçekleştirir.
MusicProvider
Müzik üretir veya sağlar.
SoundEffectProvider
Ses efektlerini sağlar.
Her provider kendi:
authentication
request
polling
timeout
retry
response parsing
download
işlemlerinden sorumludur.
Hermes'in ana workflow katmanı provider'a özel API ayrıntılarını bilmemelidir.

## 1.10 Provider Selection
Provider seçimi deterministic policy ile yapılmalıdır.
Örnek kriterler:
test / production mode
requested quality
cost limit
video duration
supported aspect ratio
required resolution
generation speed
provider availability
retry state
content compatibility
Örnek:
TEST MODE:
LocalTestVideoProvider
PRODUCTION MODE:
SeedanceProvider
Fallback:
AlternativeVideoProvider
Hermes rastgele provider değiştirmemelidir.
Provider seçimi configuration ve policy tarafından kontrol edilmelidir.

## 1.11 Video Editing Engine
Video üretim servisi final videoyu oluşturmak zorunda değildir.
AI video provider tarafından oluşturulan klipler ham asset olarak kabul edilir.
Final video Hermes Editing Engine tarafından hazırlanır.
Ana teknoloji:
FFmpeg
Hermes sisteminde doğrulanmış FFmpeg binary mevcut olduğu için temel media engine olarak kullanılacaktır.
FFmpeg görevleri:
probe
trim
concatenate
transcode
audio normalization
audio mixing
video scaling
crop
aspect ratio normalization
frame rate normalization
codec conversion
muxing
final technical inspection

## 1.12 Programmatic Composition Layer
Programatik video composition için:
Remotion
kullanılacaktır.
Remotion aşağıdaki görevlerde kullanılabilir:
timeline composition
titles
animated text
lower thirds
overlays
branded layouts
transitions
charts
progress indicators
subtitles
reusable visual templates
FFmpeg ve Remotion birbirinin alternatifi değildir.
FFmpeg media processing engine'dir.
Remotion programmatic composition engine'dir.
Hermes ikisini birlikte kullanabilir.

## 1.13 Voice and Audio Layer
Ses üretimi provider-independent olacaktır.
Interface:
VoiceProvider
Development başlangıcında:
local/free TTS
Edge TTS
Piper
gibi düşük maliyetli seçenekler kullanılabilir.
Production aşamasında farklı voice provider'lar eklenebilir.
Audio pipeline:
Voice generation
↓
Audio validation
↓
Noise / silence processing
↓
Volume normalization
↓
Timeline alignment
↓
Music/SFX mix
↓
Final audio track

## 1.14 Caption and Subtitle Layer
Subtitle sistemi ayrı bir modül olacaktır.
Kaynak:
original script timing
voice alignment
speech recognition
Whisper veya başka transcription provider
Output formatları:
SRT
VTT
structured caption JSON
Hermes gerektiğinde:
soft subtitles
veya
burned-in captions
üretebilmelidir.
Short-form içerikte burned-in dynamic captions desteklenmelidir.

## 1.15 Render Layer
Render Engine tüm hazır elementleri final medya dosyasına dönüştürür.
Input:
video clips
images
voice
music
SFX
captions
overlays
timeline
platform profile
Output:
RenderArtifact
En az:
file path
checksum
codec
resolution
duration
fps
audio codec
aspect ratio
size
bilgilerini içermelidir.

## 1.16 Validation Layer
Bir video render edildi diye otomatik olarak başarılı kabul edilmemelidir.
Final artifact doğrulanmalıdır.
Technical Validation
Kontroller:
file exists
file readable
valid container
supported codec
expected resolution
expected duration
expected FPS
audio exists
no corrupt stream
expected aspect ratio
file size boundaries
FFprobe bu doğrulamanın temel araçlarından biri olacaktır.
Content Validation
Kontroller:
scenes present
narration consistency
captions present
no missing assets
intended duration
platform requirements
required CTA
branding rules
Validation geçmeden publishing aşaması başlamamalıdır.

## 1.17 Publishing Architecture
Publishing sistemi de provider-independent olacaktır.
Temel interface:
PublishingProvider
Implementasyon örnekleri:
YouTubePublisher
TikTokPublisher
InstagramPublisher
FacebookPublisher
İleride yeni platformlar yalnızca yeni publisher implementasyonu eklenerek desteklenebilmelidir.
Ana Hermes pipeline değişmemelidir.

## 1.18 Platform Adaptation
Tek final video her platforma doğrudan gönderilmek zorunda değildir.
Hermes platform profil sistemi kullanacaktır.
Örnek profiller:
YouTubeLongFormProfile
YouTubeShortsProfile
TikTokProfile
InstagramReelsProfile
FacebookReelsProfile
Profile aşağıdakileri tanımlar:
aspect ratio
resolution
max/min duration
title requirements
description rules
caption style
thumbnail rules
metadata rules
publishing requirements
Bu sayede aynı içerikten farklı platform çıktıları üretilebilir.

## 1.19 Scheduling
Publishing işlemi anında veya zamanlanmış olabilir.
Her PublishJob:
platform
account
artifact
scheduled_at
metadata
status
retry_count
bilgilerini taşır.
Scheduler yalnızca zamanı gelmiş ve validasyonu geçmiş işleri publishing queue'ya gönderir.

## 1.20 Queue and Job Execution
Uzun süren media işlemleri synchronous request içinde yürütülmemelidir.
Video generation, render ve upload işlemleri job tabanlı olmalıdır.
Temel durumlar:
PENDING
RUNNING
WAITING_PROVIDER
VALIDATING
COMPLETED
FAILED
RETRY_PENDING
CANCELLED
Job state değişimleri audit edilmelidir.

## 1.21 Retry and Failure Recovery
Her hata aynı şekilde retry edilmemelidir.
Hatalar sınıflandırılmalıdır.
Örnek:
Retryable
timeout
temporary provider failure
rate limit
transient network failure
Non-Retryable
invalid credentials
unsupported media format
policy rejection
corrupted source asset
invalid configuration
Retry:
bounded
deterministic
logged
auditable
olmalıdır.
Infinite retry yasaktır.

## 1.22 Audit and Evidence Integration
Hermes Core mevcut Audit Engine ve Evidence Chain mekanizmaları video pipeline'a entegre edilecektir.
Audit örnekleri:
VideoJob created
research completed
script generated
scene plan generated
provider selected
generation requested
asset downloaded
voice generated
render started
render completed
validation passed
publishing requested
upload completed
publish failed
retry scheduled
Bu kayıtlar üretim sürecinin tamamının izlenebilir olmasını sağlar.

## 1.23 Cost Control
Cost control sistemin temel gereksinimlerinden biridir.
Her ücretli provider çağrısı:
provider
operation
estimated cost
actual cost if available
job_id
timestamp
ile ilişkilendirilmelidir.
Development sırasında default politika:
Paid provider calls disabled
olmalıdır.
Production sırasında bütçe politikaları uygulanmalıdır.
Örneğin:
maximum cost per video
maximum daily generation cost
maximum retry cost
provider-specific limits

## 1.24 Security and Credentials
API anahtarları source code içine yazılmayacaktır.
Credentials:
environment variables
secure secret storage
provider-specific credential objects
üzerinden yönetilecektir.
Her sosyal medya hesabı ayrı credential context kullanmalıdır.
Video provider credentials ile social publishing credentials birbirinden ayrılmalıdır.

## 1.25 Isolation From Other Hermes Pipelines
Video Automation, Hermes'in diğer üretim sistemlerinden bağımsız olacaktır.
Özellikle ileride kurulacak Website Factory/Web Studio ile:
media job'ları
configuration
provider registry
templates
project state
output directories
credentials
deployment logic
karıştırılmamalıdır.
Paylaşılan tek alan Hermes Core servisleri olabilir.
Video Automation kendi domain sınırlarına sahip olacaktır.

## 1.26 Explicit Project Separation
Hermes Video Automation yalnızca Hermes projesine aittir.
Başka ürün veya proje mimarileri bu dokümana dahil edilmemelidir.
Repository, documentation, configuration, secrets, provider definitions, roadmap ve implementation state Hermes'e özgü tutulacaktır.

## 1.27 Definition of Success
Hermes Video Automation ilk production-ready sürümünde aşağıdaki işlemi güvenilir şekilde gerçekleştirebilmelidir:
Bir VideoJob alır.
↓
İçeriği hazırlar.
↓
Senaryoyu üretir.
↓
Scene ve shot planı oluşturur.
↓
Gerekli media asset'lerini provider'lardan toplar veya üretir.
↓
Voice ve audio oluşturur.
↓
Videoyu otomatik kurgular.
↓
Altyazıları ekler.
↓
Final videoyu render eder.
↓
Teknik ve içerik validasyonunu gerçekleştirir.
↓
Platforma uygun versiyonları üretir.
↓
Yetkili sosyal medya hesaplarında yayınlar veya zamanlar.
↓
Her işlemi Hermes Audit/Evidence sistemine kaydeder.
Bu işlem minimum manuel müdahale ile tekrar tekrar çalıştırılabilmelidir.

## 1.28 Canonical Architectural Rule
Hermes Video Automation'ın değişmez ana prensibi:
Hermes workflow'u yönetir; provider'lar işleri gerçekleştirir; hiçbir provider Hermes'in mimarisini belirlemez.
Seedance, FFmpeg, Remotion, Whisper, YouTube, TikTok, Instagram veya Facebook sistemin kendisi değildir.
Bunların tamamı değiştirilebilir entegrasyonlardır.
Hermes Video Automation kalıcı olan orchestration, domain model, validation, policy, audit ve workflow katmanıdır.
