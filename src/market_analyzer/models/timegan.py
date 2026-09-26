"""PyTorch implementation of the core TimeGAN architecture and training phases.

The architecture follows the original Embedder/Recovery/Generator/Supervisor/Discriminator
design while using modern PyTorch primitives instead of the original TensorFlow 1.x stack.
"""
from __future__ import annotations
from dataclasses import dataclass
import torch
from torch import nn

@dataclass
class TimeGANConfig:
    feature_dim:int
    hidden_dim:int=64
    num_layers:int=2
    latent_dim:int|None=None
    dropout:float=0.0
    def __post_init__(self):
        if self.latent_dim is None:self.latent_dim=self.feature_dim

class RNNStack(nn.Module):
    def __init__(self,input_dim,hidden_dim,num_layers,dropout):
        super().__init__()
        self.rnn=nn.GRU(input_dim,hidden_dim,num_layers=num_layers,batch_first=True,dropout=dropout if num_layers>1 else 0.0)
    def forward(self,x): return self.rnn(x)[0]

class TimeGAN(nn.Module):
    def __init__(self,config:TimeGANConfig):
        super().__init__()
        h=config.hidden_dim; z=int(config.latent_dim); d=config.feature_dim
        self.embedder=RNNStack(d,h,config.num_layers,config.dropout)
        self.recovery=nn.Sequential(nn.Linear(h,h),nn.Sigmoid(),nn.Linear(h,d))
        self.generator=RNNStack(z,h,config.num_layers,config.dropout)
        self.supervisor=RNNStack(h,h,max(1,config.num_layers-1),config.dropout)
        self.discriminator=nn.Sequential(nn.Linear(h,h),nn.LeakyReLU(0.2),nn.Linear(h,1))
    def embed(self,x): return self.embedder(x)
    def recover(self,h): return self.recovery(h)
    def generate_latent(self,z): return self.supervisor(self.generator(z))
    def generate(self,z): return self.recover(self.generate_latent(z))
    def discriminate(self,h): return self.discriminator(h[:,-1,:]).squeeze(-1)

def reconstruction_loss(x,x_tilde): return nn.functional.mse_loss(x_tilde,x)

def supervised_loss(h,h_supervised):
    if h.size(1)<2:return h.new_tensor(0.0)
    return nn.functional.mse_loss(h[:,1:,:],h_supervised[:,:-1,:])

def moment_loss(x,x_hat):
    return torch.abs(x.mean((0,1))-x_hat.mean((0,1))).mean()+torch.abs(x.std((0,1))-x_hat.std((0,1))).mean()

def adversarial_loss(logits,real):
    target=torch.ones_like(logits) if real else torch.zeros_like(logits)
    return nn.functional.binary_cross_entropy_with_logits(logits,target)

class TimeGANTrainer:
    def __init__(self,model:TimeGAN,lr=1e-3,device=None):
        self.model=model
        self.device=device or ("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
        self.model.to(self.device)
        self.opt_embed=torch.optim.Adam(list(model.embedder.parameters())+list(model.recovery.parameters()),lr=lr)
        self.opt_gen=torch.optim.Adam(list(model.generator.parameters())+list(model.supervisor.parameters()),lr=lr)
        self.opt_disc=torch.optim.Adam(model.discriminator.parameters(),lr=lr)

    def _noise(self,batch,steps):
        return torch.rand(batch,steps,self.model.generator.rnn.input_size,device=self.device)

    def reconstruction_step(self,x):
        x=x.to(self.device)
        h=self.model.embed(x); recon=self.model.recover(h)
        loss=reconstruction_loss(x,recon)
        self.opt_embed.zero_grad();loss.backward();self.opt_embed.step()
        return float(loss.detach().cpu())

    def generator_step(self,x):
        x=x.to(self.device);h=self.model.embed(x).detach()
        z=self._noise(x.size(0),x.size(1));fake_h=self.model.generate_latent(z);fake_x=self.model.recover(fake_h)
        sup=supervised_loss(h,self.model.supervisor(h))
        adv=adversarial_loss(self.model.discriminate(fake_h),True)
        loss=adv+100.0*sup+100.0*moment_loss(x,fake_x)
        self.opt_gen.zero_grad();loss.backward();self.opt_gen.step()
        return float(loss.detach().cpu())

    def discriminator_step(self,x):
        x=x.to(self.device);z=self._noise(x.size(0),x.size(1))
        with torch.no_grad(): real_h=self.model.embed(x);fake_h=self.model.generate_latent(z)
        real_loss=adversarial_loss(self.model.discriminate(real_h),True)
        fake_loss=adversarial_loss(self.model.discriminate(fake_h),False)
        loss=real_loss+fake_loss
        self.opt_disc.zero_grad();loss.backward();self.opt_disc.step()
        return float(loss.detach().cpu())

    def fit(self,loader,epochs=10):
        history=[]
        for _ in range(epochs):
            losses={"reconstruction":0.0,"generator":0.0,"discriminator":0.0,"batches":0}
            for batch in loader:
                x=batch[0] if isinstance(batch,(tuple,list)) else batch
                losses["reconstruction"]+=self.reconstruction_step(x)
                losses["generator"]+=self.generator_step(x)
                losses["discriminator"]+=self.discriminator_step(x)
                losses["batches"]+=1
            n=max(losses.pop("batches"),1)
            history.append({k:v/n for k,v in losses.items()})
        return history

    @torch.no_grad()
    def sample(self,num_samples,seq_len):
        z=self._noise(num_samples,seq_len)
        return self.model.generate(z).detach().cpu()
