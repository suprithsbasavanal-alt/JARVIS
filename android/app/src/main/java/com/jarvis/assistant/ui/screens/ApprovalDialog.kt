package com.jarvis.assistant.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Fingerprint
import androidx.compose.material.icons.filled.Security
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import com.jarvis.assistant.data.model.ApprovalCardDto
import com.jarvis.assistant.ui.theme.*

@Composable
fun ApprovalDialog(
    card: ApprovalCardDto,
    onApprove: (String) -> Unit,
    onDeny: (String) -> Unit
) {
    Dialog(onDismissRequest = { onDeny(card.cardId) }) {
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(20.dp)),
            color = DarkSurface,
            border = BorderStroke(1.5.dp, AuricGold),
            shape = RoundedCornerShape(20.dp)
        ) {
            Column(
                modifier = Modifier.padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Header
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Security,
                        contentDescription = "Security Alert",
                        tint = AuricGold
                    )
                    Text(
                        text = "HUMAN CONFIRMATION REQUIRED",
                        style = MaterialTheme.typography.labelSmall,
                        color = AuricGold,
                        fontWeight = FontWeight.Bold
                    )
                }

                // Details
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(
                        text = "Tool: ${card.toolName}",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                        color = ElectricCyan
                    )
                    Text(
                        text = "Target: ${card.targetResource}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = TextPrimary
                    )
                    Text(
                        text = "Risk Level: ${card.riskLevel}",
                        style = MaterialTheme.typography.labelSmall,
                        color = if (card.riskLevel == "HIGH") DangerCrimson else AuricGold
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = card.reasoningSummary,
                        style = MaterialTheme.typography.bodyLarge,
                        color = TextSecondary
                    )
                }

                // Action Buttons
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    OutlinedButton(
                        onClick = { onDeny(card.cardId) },
                        modifier = Modifier.weight(1f).height(48.dp),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = DangerCrimson),
                        border = BorderStroke(1.dp, DangerCrimson)
                    ) {
                        Text("DENY", fontWeight = FontWeight.Bold)
                    }

                    Button(
                        onClick = { onApprove(card.cardId) },
                        modifier = Modifier.weight(1f).height(48.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = ElectricCyan, contentColor = DarkVoid)
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                            Icon(Icons.Default.Fingerprint, contentDescription = "Biometric", modifier = Modifier.size(18.dp))
                            Text("APPROVE", fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }
    }
}
