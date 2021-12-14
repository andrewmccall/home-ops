#ansible

First get all the requirements

``` ansible-galaxy install -r requirements.yaml ```

Then do the install

``` 
    export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
    ansible-playbook playbooks/cluster/k3s.yaml
```

download the kubeconfig and replace 127.0.0.1 with the right host. 
