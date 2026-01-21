# Database - Supabase Configuration

Open Notebook uses Supabase for its database needs. 

---

## Default Configuration

Open Notebook should work out of the box with Supabase as long as the environment variables are correctly setup. 


### DB running in the same docker compose as Open Notebook (recommended)

The example above is for when you are running Supabase as a separate docker container, which is the method described [here](../1-INSTALLATION/docker-compose.md) (and our recommended method). 

```env
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_ANON_KEY="your-anon-key"
```

### DB running in the host machine and Open Notebook running in Docker

If ON is running in docker and Supabase is on your host machine, you need to point to it. 

```env
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_ANON_KEY="your-anon-key"
```

### Open Notebook and Supabase are running on the same machine

If you are running both services locally or if you are using the [single container setup](../1-INSTALLATION/single-container.md)

```env
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_ANON_KEY="your-anon-key"
```

## Multiple databases

You can have multiple projects in one Supabase instance and you can also have multiple databases in one instance. So, if you want to setup multiple open notebook deployments for different users, you don't need to deploy multiple databases. 
