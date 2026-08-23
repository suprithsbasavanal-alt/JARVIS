package com.jarvis.assistant

import android.app.Application
import android.util.Log

class JarvisApplication : Application() {

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "Initializing JARVIS Android Companion Client (Phase 8.1 Bootstrap)")
    }

    companion object {
        const val TAG = "JarvisApplication"
    }
}
