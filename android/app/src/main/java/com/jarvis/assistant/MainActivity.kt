package com.jarvis.assistant

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.jarvis.assistant.security.StandardBiometricAuthManager
import com.jarvis.assistant.ui.screens.*
import com.jarvis.assistant.ui.theme.*
import com.jarvis.assistant.viewmodel.CompanionTab
import com.jarvis.assistant.viewmodel.MainViewModel

class MainActivity : ComponentActivity() {

    private val viewModel: MainViewModel by viewModels {
        object : androidx.lifecycle.ViewModelProvider.Factory {
            override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
                @Suppress("UNCHECKED_CAST")
                return MainViewModel(
                    biometricAuthManager = StandardBiometricAuthManager(this@MainActivity)
                ) as T
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            JarvisTheme {
                MainCompanionApp(viewModel = viewModel)
            }
        }
    }
}

@Composable
fun MainCompanionApp(viewModel: MainViewModel) {
    val selectedTab by viewModel.selectedTab.collectAsState()
    val isConnected by viewModel.isConnected.collectAsState()
    val status by viewModel.status.collectAsState()
    val messages by viewModel.messages.collectAsState()
    val pendingApproval by viewModel.pendingApproval.collectAsState()
    val proactiveAdvisory by viewModel.proactiveAdvisory.collectAsState()
    val activePlan by viewModel.activePlan.collectAsState()

    Scaffold(
        bottomBar = {
            NavigationBar(
                containerColor = DarkSurfaceElevated,
                contentColor = TextPrimary
            ) {
                NavigationBarItem(
                    selected = selectedTab == CompanionTab.DASHBOARD,
                    onClick = { viewModel.selectTab(CompanionTab.DASHBOARD) },
                    icon = { Icon(Icons.Default.Dashboard, contentDescription = "Dashboard") },
                    label = { Text("Dashboard") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = ElectricCyan,
                        selectedTextColor = ElectricCyan,
                        indicatorColor = DarkSurface
                    )
                )
                NavigationBarItem(
                    selected = selectedTab == CompanionTab.CHAT,
                    onClick = { viewModel.selectTab(CompanionTab.CHAT) },
                    icon = { Icon(Icons.Default.Chat, contentDescription = "Chat") },
                    label = { Text("Chat") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = ElectricCyan,
                        selectedTextColor = ElectricCyan,
                        indicatorColor = DarkSurface
                    )
                )
                NavigationBarItem(
                    selected = selectedTab == CompanionTab.PROACTIVE,
                    onClick = { viewModel.selectTab(CompanionTab.PROACTIVE) },
                    icon = { Icon(Icons.Default.Lightbulb, contentDescription = "Advisory") },
                    label = { Text("Advisory") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = AuricGold,
                        selectedTextColor = AuricGold,
                        indicatorColor = DarkSurface
                    )
                )
                NavigationBarItem(
                    selected = selectedTab == CompanionTab.PLANS,
                    onClick = { viewModel.selectTab(CompanionTab.PLANS) },
                    icon = { Icon(Icons.Default.Checklist, contentDescription = "Plans") },
                    label = { Text("Plans") },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = ElectricCyan,
                        selectedTextColor = ElectricCyan,
                        indicatorColor = DarkSurface
                    )
                )
            }
        },
        containerColor = DarkVoid
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            when (selectedTab) {
                CompanionTab.DASHBOARD -> DashboardScreen(
                    isConnected = isConnected,
                    status = status,
                    healthScore = proactiveAdvisory?.healthScore ?: 96.5,
                    onNavigateTab = { viewModel.selectTab(it) },
                    onEmergencyStop = { viewModel.triggerEmergencyStop() }
                )
                CompanionTab.CHAT -> ChatScreen(
                    messages = messages,
                    onSendMessage = { viewModel.sendQuery(it) }
                )
                CompanionTab.PROACTIVE -> ProactiveScreen(
                    advisory = proactiveAdvisory
                )
                CompanionTab.PLANS -> PlanScreen(
                    plan = activePlan,
                    onToggleStep = { planId, stepNum, completed ->
                        viewModel.toggleStep(planId, stepNum, completed)
                    }
                )
            }

            // Biometric HITL Approval Dialog
            pendingApproval?.let { card ->
                ApprovalDialog(
                    card = card,
                    onApprove = { cardId -> viewModel.handleApprovalDecision(cardId, true) },
                    onDeny = { cardId -> viewModel.handleApprovalDecision(cardId, false) }
                )
            }
        }
    }
}
