package mn.dasgaljuulagch.app;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/**
 * «Ухаалаг дасгалжуулагч»-ийн Android бүрхүүл.
 *
 * Апп өөрөө вэб хуудас (assets/www): камер, биеийн цэг илрүүлэлт (MediaPipe), зураглал нь JavaScript, давталт тоолох /
 * техник шалгах логик нь компьютерын хувилбартай ижил Python (Pyodide). Энэ класс зөвхөн:
 *   1. тэр файлуудыг https://appassets.androidplatform.net хаягаар WebView-д өгнө (ES module, WebAssembly, камер нь
 *      file:// хаягаар ажилладаггүй тул);
 *   2. камерын зөвшөөрлийг асууна;
 *   3. дэлгэцийг асаалттай байлгаж, «Буцах» товчийг хуудас хооронд ажиллуулна.
 * Бусад бүх сүлжээний хүсэлтийг хаана: апп интернэтгүй ажиллана, видео утаснаас гарахгүй.
 */
public class MainActivity extends Activity {
    private static final String HOST = "appassets.androidplatform.net";
    private static final String START_URL = "https://" + HOST + "/index.html";
    private static final String ROOT = "www";
    private static final int CAMERA_REQUEST = 1;

    private static final Map<String, String> MIME = new HashMap<>();

    static {
        MIME.put("html", "text/html");
        MIME.put("css", "text/css");
        MIME.put("js", "text/javascript");       // ES module заавал JavaScript төрөлтэй байх ёстой
        MIME.put("mjs", "text/javascript");
        MIME.put("json", "application/json");
        MIME.put("wasm", "application/wasm");    // WebAssembly.instantiateStreaming үүнийг шаардана
        MIME.put("zip", "application/zip");
        MIME.put("whl", "application/zip");
        MIME.put("svg", "image/svg+xml");
        MIME.put("png", "image/png");
        MIME.put("jpg", "image/jpeg");
        MIME.put("ico", "image/x-icon");
        MIME.put("txt", "text/plain");
    }

    private WebView webView;
    private PermissionRequest pendingCamera;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);   // дасгалын үед дэлгэц унтрахгүй

        webView = new WebView(this);
        webView.setBackgroundColor(Color.WHITE);
        webView.setOverScrollMode(View.OVER_SCROLL_NEVER);
        setContentView(webView);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);                    // тохиргоо, түүх (localStorage)
        settings.setMediaPlaybackRequiresUserGesture(false);    // камерын видео, дуут дохио
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setTextZoom(100);                              // системийн үсгийн хэмжээ дэлгэцийн зохиомжийг эвдэхгүй
        settings.setSupportZoom(false);

        webView.setWebViewClient(new AssetClient());
        webView.setWebChromeClient(new CameraClient());
        webView.addJavascriptInterface(new Bridge(), "AndroidApp");

        webView.loadUrl(START_URL + startSuffix());
    }

    /**
     * Туршилтад: adb shell am start -n mn.dasgaljuulagch.app/.MainActivity --es open "?selftest=1&demo=1#/workout"
     * гэж эхлүүлбэл тэр хуудсыг шууд нээнэ (ci_emulator_test.sh). Зөвхөн аппын өөрийн хуудасны хаягийн төгсгөл.
     */
    private String startSuffix() {
        String open = getIntent() == null ? null : getIntent().getStringExtra("open");
        return open != null && open.matches("[?#][A-Za-z0-9_=&/#?.-]{0,80}") ? open : "";
    }

    /** assets/www доторх файлыг буцаана. Аппын биш бүх хаягт 404: WebView сүлжээ рүү огт гарахгүй. */
    private class AssetClient extends WebViewClient {
        @Override
        public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
            Uri uri = request.getUrl();
            String scheme = uri.getScheme();
            if ("data".equals(scheme) || "blob".equals(scheme) || "about".equals(scheme)) {
                return null;
            }
            if (!"https".equals(scheme) || !HOST.equals(uri.getHost())) {
                return notFound();
            }
            String path = uri.getPath();
            if (path == null || path.isEmpty() || path.equals("/")) {
                path = "/index.html";
            }
            if (path.contains("..")) {
                return notFound();
            }
            try {
                InputStream in = getAssets().open(ROOT + path);
                Map<String, String> headers = new HashMap<>();
                headers.put("Cache-Control", "no-cache");
                headers.put("Access-Control-Allow-Origin", "*");
                String mime = mimeOf(path);
                String encoding = mime.startsWith("text/") || mime.equals("application/json") ? "utf-8" : null;
                return new WebResourceResponse(mime, encoding, 200, "OK", headers, in);
            } catch (IOException e) {
                return notFound();
            }
        }

        @Override
        public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            return !HOST.equals(request.getUrl().getHost());   // аппаас гадагш шилжихгүй
        }
    }

    private static String mimeOf(String path) {
        int dot = path.lastIndexOf('.');
        String ext = dot < 0 ? "" : path.substring(dot + 1).toLowerCase(Locale.ROOT);
        String mime = MIME.get(ext);
        return mime != null ? mime : "application/octet-stream";
    }

    private static WebResourceResponse notFound() {
        return new WebResourceResponse("text/plain", "utf-8", 404, "Not Found", new HashMap<String, String>(),
                new ByteArrayInputStream(new byte[0]));
    }

    /** Хуудас камер асуухад (getUserMedia) Android-ын зөвшөөрлийг шалгаж / асууж хариулна. */
    private class CameraClient extends WebChromeClient {
        @Override
        public void onPermissionRequest(final PermissionRequest request) {
            boolean video = false;
            for (String resource : request.getResources()) {
                if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(resource)) {
                    video = true;
                }
            }
            if (!video) {
                request.deny();
                return;
            }
            if (checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
                grantCamera(request);
                return;
            }
            if (pendingCamera != null) {
                pendingCamera.deny();
            }
            pendingCamera = request;
            requestPermissions(new String[] {Manifest.permission.CAMERA}, CAMERA_REQUEST);
        }

        @Override
        public void onPermissionRequestCanceled(PermissionRequest request) {
            if (request == pendingCamera) {
                pendingCamera = null;
            }
        }
    }

    private static void grantCamera(PermissionRequest request) {
        request.grant(new String[] {PermissionRequest.RESOURCE_VIDEO_CAPTURE});
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != CAMERA_REQUEST || pendingCamera == null) {
            return;
        }
        PermissionRequest request = pendingCamera;
        pendingCamera = null;
        if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            grantCamera(request);
        } else {
            request.deny();   // хуудас «Камер нээгдсэнгүй» самбар, демо горимын сонголтыг үзүүлнэ
        }
    }

    /** Хуудаснаас дуудах функцууд: window.AndroidApp. */
    private class Bridge {
        /** Цайвар / харанхуй горим солигдоход системийн самбаруудын өнгийг тааруулна. */
        @JavascriptInterface
        public void setTheme(final boolean dark) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    applyBars(dark);
                }
            });
        }
    }

    private void applyBars(boolean dark) {
        Window window = getWindow();
        int color = dark ? Color.rgb(20, 20, 20) : Color.WHITE;
        int flags = window.getDecorView().getSystemUiVisibility();
        int light = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR;
        window.setStatusBarColor(color);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            light |= View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR;
            window.setNavigationBarColor(color);
        }
        window.getDecorView().setSystemUiVisibility(dark ? flags & ~light : flags | light);
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();     // хуудас бүр хаягийн # хэсгээр ялгагддаг тул өмнөх хуудас руу буцна
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onPause() {
        webView.onPause();        // хуудас далд орсныг мэдээд дасгалыг зогсоож, камерыг чөлөөлнө
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        webView.onResume();
    }

    @Override
    protected void onDestroy() {
        if (pendingCamera != null) {
            pendingCamera.deny();
            pendingCamera = null;
        }
        webView.destroy();
        super.onDestroy();
    }
}
