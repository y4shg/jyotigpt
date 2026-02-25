<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { JYOTIGPT_NAME, showSidebar, user } from '$lib/stores';
	import SidebarIcon from '$lib/components/icons/SidebarIcon.svelte';
	import { page } from '$app/stores';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		}
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Admin Panel')} | {$JYOTIGPT_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div
		class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-260px)]'
			: ''} max-w-full"
	>
		<nav class="px-2.5 pt-1 backdrop-blur-xl drag-region">
			<div class=" flex items-center gap-1">
				<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center self-end">
					<button
						id="sidebar-toggle-button"
						class="btn-ghost p-1.5 rounded-xl"
						on:click={() => {
							showSidebar.set(!$showSidebar);
						}}
						aria-label="Toggle Sidebar"
					>
						<div class=" m-auto self-center">
							<SidebarIcon />
						</div>
					</button>
				</div>

				<div class=" flex w-full">
					<div
						class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-surface/60 border border-border px-1 py-0.5"
					>
						<a
							class="min-w-fit rounded-full px-3 py-1.5 {['/admin/users'].includes($page.url.pathname)
								? 'bg-primary-600 text-primary-foreground'
								: 'text-gray-500 dark:text-gray-400 hover:text-foreground'} transition"
							href="/admin">{$i18n.t('Users')}</a
						>

						<a
							class="min-w-fit rounded-full px-3 py-1.5 {$page.url.pathname.includes('/admin/evaluations')
								? 'bg-primary-600 text-primary-foreground'
								: 'text-gray-500 dark:text-gray-400 hover:text-foreground'} transition"
							href="/admin/evaluations">{$i18n.t('Evaluations')}</a
						>

						<a
							class="min-w-fit rounded-full px-3 py-1.5 {$page.url.pathname.includes('/admin/functions')
								? 'bg-primary-600 text-primary-foreground'
								: 'text-gray-500 dark:text-gray-400 hover:text-foreground'} transition"
							href="/admin/functions">{$i18n.t('Functions')}</a
						>

						<a
							class="min-w-fit rounded-full px-3 py-1.5 {$page.url.pathname.includes('/admin/settings')
								? 'bg-primary-600 text-primary-foreground'
								: 'text-gray-500 dark:text-gray-400 hover:text-foreground'} transition"
							href="/admin/settings">{$i18n.t('Settings')}</a
						>
					</div>
				</div>
			</div>
		</nav>

		<div class=" pb-4 px-[16px] flex-1 max-h-full overflow-y-auto">
			<slot />
		</div>
	</div>
{/if}
