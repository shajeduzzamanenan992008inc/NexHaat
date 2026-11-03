package com.nexhaat.app.data.session

import com.nexhaat.app.data.remote.dto.UserDto

sealed interface SessionState {
    data object Unknown : SessionState
    data object Unauthenticated : SessionState
    data class Authenticated(val user: UserDto) : SessionState
}
