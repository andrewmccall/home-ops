#ansible

First get all the requirements, you may need to do this with a --force.

``` ansible-galaxy install -r requirements.yaml ```

Then do the install:

``` 
    export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
    ansible-playbook playbooks/all.yaml
```

download the kubeconfig and replace 127.0.0.1 with the right host. 
