# TODO: Set up dual GitHub SSH accounts

Pain point: switching between `renjialan` (personal) and work GitHub account requires re-auth each time.

## Steps

1. Generate SSH keys if not already done:
   ```bash
   ssh-keygen -t ed25519 -C "oliveren88@gmail.com" -f ~/.ssh/id_personal
   ssh-keygen -t ed25519 -C "work@company.com" -f ~/.ssh/id_work
   ```

2. Add to `~/.ssh/config` (manage via chezmoi):
   ```
   Host github-personal
     HostName github.com
     User git
     IdentityFile ~/.ssh/id_personal

   Host github-work
     HostName github.com
     User git
     IdentityFile ~/.ssh/id_work
   ```

3. Add public keys to each GitHub account (Settings → SSH keys).

4. Update remote URL for this repo:
   ```bash
   git remote set-url origin git@github-personal:renjialan/financebuddy.git
   ```

5. Add chezmoi to dotfiles repo so it follows you across machines.
