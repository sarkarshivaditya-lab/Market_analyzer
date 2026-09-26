"""Modern PyTorch TimeGAN implementation based on the upstream 2019 architecture."""
from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn


@dataclass
class TimeGANConfig:
    feature_dim: int
    hidden_dim: int = 64
    num_layers: int = 2
    latent_dim: int | None = None
    dropout: float = 0.0

    def __post_init__(self) -> None:
        if self.latent_dim is None:
            self.latent_dim = self.feature_dim


class RNNStack(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_layers: int, dropout: float):
        super().__init__()
        self.rnn = nn.GRU(
            input_dim,
            hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.rnn(x)[0]


class TimeGAN(nn.Module):
    """Embedder + recovery + generator + supervisor + discriminator."""

    def __init__(self, config: TimeGANConfig):
        super().__init__()
        h = config.hidden_dim
        z = int(config.latent_dim)
        d = config.feature_dim
        self.hidden_dim = h
        self.latent_dim = z
        self.embedder = RNNStack(d, h, config.num_layers, config.dropout)
        self.recovery = nn.Sequential(nn.Linear(h, h), nn.Sigmoid(), nn.Linear(h, d))
        self.generator = RNNStack(z, h, config.num_layers, config.dropout)
        self.supervisor = RNNStack(h, h, max(1, config.num_layers - 1), config.dropout)
        self.discriminator = nn.Sequential(nn.Linear(h, h), nn.LeakyReLU(0.2), nn.Linear(h, 1))

    def embed(self, x: torch.Tensor) -> torch.Tensor:
        return self.embedder(x)

    def recover(self, h: torch.Tensor) -> torch.Tensor:
        return self.recovery(h)

    def generate(self, z: torch.Tensor) -> torch.Tensor:
        e_hat = self.generator(z)
        h_hat = self.supervisor(e_hat)
        return self.recover(h_hat)

    def discriminate(self, h: torch.Tensor) -> torch.Tensor:
        return self.discriminator(h[:, -1, :]).squeeze(-1)

    def forward(self, x: torch.Tensor, z: torch.Tensor) -> dict[str, torch.Tensor]:
        h = self.embed(x)
        x_tilde = self.recover(h)
        x_hat = self.generate(z)
        h_hat = self.generator(z)
        h_supervised = self.supervisor(h)
        return {
            "h": h,
            "x_tilde": x_tilde,
            "x_hat": x_hat,
            "h_hat": h_hat,
            "h_supervised": h_supervised,
        }


def reconstruction_loss(x: torch.Tensor, x_tilde: torch.Tensor) -> torch.Tensor:
    return nn.functional.mse_loss(x_tilde, x)


def supervised_loss(h: torch.Tensor, h_supervised: torch.Tensor) -> torch.Tensor:
    if h.size(1) < 2:
        return h.new_tensor(0.0)
    return nn.functional.mse_loss(h[:, 1:, :], h_supervised[:, :-1, :])


def moment_loss(x: torch.Tensor, x_hat: torch.Tensor) -> torch.Tensor:
    mean_loss = torch.abs(x.mean(dim=(0, 1)) - x_hat.mean(dim=(0, 1))).mean()
    std_loss = torch.abs(x.std(dim=(0, 1)) - x_hat.std(dim=(0, 1))).mean()
    return mean_loss + std_loss


def adversarial_loss(logits: torch.Tensor, real: bool) -> torch.Tensor:
    targets = torch.ones_like(logits) if real else torch.zeros_like(logits)
    return nn.functional.binary_cross_entropy_with_logits(logits, targets)
