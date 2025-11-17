import torch
import torch.nn as nn

class MultiTaskDINOv2(nn.Module):
    def __init__(self, dropout_rate=0.3, freeze_backbone=False):
        super(MultiTaskDINOv2, self).__init__()
        self.backbone = torch.hub.load("facebookresearch/dinov2", "dinov2_vits14_lc")
        self.backbone.head = nn.Identity()

        if freeze_backbone:
            for param in self.backbone.parameters():
                param.requires_grad = False

        # Hai head riêng: Task 1 (age), Task 2 (phone usage)
        self.age_head = nn.Sequential(
            nn.Dropout(dropout_rate),
            nn.Linear(1000, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate),
            nn.Linear(512, 2)  # adult/child
        )
        self.phone_head = nn.Sequential(
            nn.Dropout(dropout_rate),
            nn.Linear(1000, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate),
            nn.Linear(512, 2)  # use/not_use
        )

    def forward(self, x):
        feat = self.backbone(x)
        age_logits = self.age_head(feat)
        phone_logits = self.phone_head(feat)
        return age_logits, phone_logits
