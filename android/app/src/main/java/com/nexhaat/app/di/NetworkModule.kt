package com.nexhaat.app.di

import com.nexhaat.app.BuildConfig
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import com.nexhaat.app.data.remote.ApiService
import com.nexhaat.app.data.remote.interceptor.CsrfInterceptor
import com.nexhaat.app.data.remote.interceptor.SafeNetworkLoggingInterceptor
import com.nexhaat.app.data.remote.interceptor.SessionExpiryInterceptor
import com.nexhaat.app.data.remote.interceptor.PersistentCookieJar
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideJson(): Json = Json {
        ignoreUnknownKeys = true
        coerceInputValues = true
    }

    @Provides
    @Singleton
    fun provideCookieJar(): PersistentCookieJar = PersistentCookieJar()

    @Provides
    @Singleton
    fun provideCsrfInterceptor(): CsrfInterceptor = CsrfInterceptor()

    @Provides
    @Singleton
    fun provideOkHttpClient(
        cookieJar: PersistentCookieJar,
        csrfInterceptor: CsrfInterceptor,
        sessionExpiryInterceptor: SessionExpiryInterceptor
    ): OkHttpClient {
        val builder = OkHttpClient.Builder()
            .cookieJar(cookieJar)
            .addInterceptor(csrfInterceptor)
            .addInterceptor(sessionExpiryInterceptor)
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
        if (BuildConfig.DEBUG) {
            builder.addInterceptor(SafeNetworkLoggingInterceptor())
        }
        return builder.build()
    }

    @Provides
    @Singleton
    fun provideRetrofit(json: Json, okHttpClient: OkHttpClient): Retrofit {
        val contentType = "application/json".toMediaType()
        return Retrofit.Builder()
            .baseUrl(BuildConfig.BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(json.asConverterFactory(contentType))
            .build()
    }

    @Provides
    @Singleton
    fun provideApiService(retrofit: Retrofit): ApiService {
        return retrofit.create(ApiService::class.java)
    }
}
